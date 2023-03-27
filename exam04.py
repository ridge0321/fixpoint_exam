# 設問4
from datetime import datetime
from collections import deque
from typing import Dict, Union
from copy import deepcopy
import ipaddress as ipad


class init_param:
    """
    入力されるパラメータを管理するオブジェクト
    変数名は問題文に準拠する
    """

    def __init__(self) -> None:
        print("N回以上連続してタイムアウトした場合にのみ故障とみなします")
        print("Nの値を入力してください")
        self._N = int(input())

        print("直近m回の平均応答時間がtミリ秒を超えた場合は、サーバが過負荷状態になっているとみなします。")
        print("mの値を入力してください")
        self._M = int(input())

        print("tの値を入力してください")
        self._T = int(input())


class Ping_log:
    """
    ログ一行分の日付、アドレス、応答結果を管理するためのクラス
    """

    def __init__(self, f_line) -> None:
        # 一行分のログを日付、アドレス、応答結果に分割
        str_date, str_ip, str_res = map(str, f_line.split(","))
        # str_ip, str_pre = map(str, str_ip_pre.split("/"))

        # オブジェクトとして保持
        self._date = datetime.strptime(str_date, "%Y%m%d%H%M%S")
        self._ip = get_ipadress_obj(str_ip)
        self._res = str_res.replace("\n", "")
        self._subnet = get_network_address(str_ip)


class Server:
    """
    各サーバーアドレスごとに値を保持するためのクラス
    """

    def __init__(self, input_value) -> None:
        self._res_que = deque()  # 直近の応答を格納するque
        self._timeout_counter: int = 0  # timeoutの連続回数のカウンター
        self._timeout_date: datetime  # timeoutを確認したログの日付
        self._overload_date: datetime  # 過負荷を確認したログの日付
        self._is_timeout: bool = False
        self._is_overload: bool = False
        self._N = input_value._N
        self._M = input_value._M

    def update_que(self, res) -> None:
        """
        新しいログを読み込んだ際にキューを更新するためのメソッド
        """
        self._res_que.append(res)

        if len(self._res_que) > self._M:
            self._res_que.popleft()

    def calc_load(self) -> int:
        """
        呼び出された時点でのサーバーの負荷を計算する
        キューの中にタイムアウトが含まれている場合は過負荷として-1を返す
        含まれていなければキューの平均値を返す
        """
        if "-" in self._res_que:
            return -1
        else:
            que_sum = sum(map(int, self._res_que))
            ave = que_sum / len(self._res_que)
        return ave

    def is_server_timeout(self):
        return self._timeout_counter >= self._N


class Subnet:
    """
    各サブネットの状態を表す値を保持するクラス
    """

    def __init__(self, subnet) -> None:
        self._server_list = []  # サブネットに含まれるサーバーの一覧
        self._is_subnet_failure = False  # サブネット全体がタイムアウトしているかどうか
        self._subnet = subnet  # ネットワークアドレス
        self._subnet_failure_date: datetime  # サブネット全てのサーバーでタイムアウトが確認された日時

    def record_failure_date(self, date: datetime):
        self._subnet_failure_date = date


def read_ping_log(FILE_PATH: str) -> list[Ping_log]:
    """
    ファイルを開きログを一行ずつ読み出すメソッド
    読み出したログはPing_log型にした後、まとめてリストで返す

    Args:
        FILE_PATH: 読み込むファイルのパス
    Returns:
        log_list: ファイルから読みだしたログ
    """

    log_list = []
    with open(FILE_PATH, "r") as f:

        for f_line in f:
            log_list.append(Ping_log(f_line))

    return log_list


def parse_log(log_list: list[Ping_log], input_value) -> list[list[str, ipad.IPv4Address, datetime, datetime]]:
    """
    Ping_log型に加工したログを読み込む

    Args:
        log_list (list[Ping_log]): 監視ログを保持しているリスト
    """

    server_dict: Dict[ipad.IPv4Address, Server] = {}  # key:サーバーのアドレス, value:Serverオブジェクト
    network_dict: Dict[ipad.IPv4Address, Subnet] = {}
    parsing_results: list[list[str, ipad.IPv4Address, datetime, datetime]] = []  # 解析結果を保持するためのリスト

    # ログを一行分ずつ解析
    for log in log_list:

        # 各サブネットごとにSubnetオブジェクトを作成
        if log._subnet not in network_dict:
            network_dict[log._subnet] = Subnet(log._subnet)

        # 各サーバーごとにServerオブジェクトを作成
        if log._ip not in server_dict:
            server_dict[log._ip] = Server(input_value)
            network_dict[log._subnet]._server_list.append(log._ip)

        # 故障期間の記録を取得
        parsing_results.append(check_failure(log, server_dict[log._ip], input_value))

        # 過負荷の記録を取得
        parsing_results.append(check_overload(log, server_dict[log._ip], input_value))

        # スイッチの故障を判定
        parsing_results.append(check_subnet_failure(log, server_dict, network_dict[log._subnet]))

    # ログ上で復旧していないサーバーの記録を加筆
    for key_ip in server_dict:
        if server_dict[key_ip]._timeout_counter >= input_value._N:
            parsing_results.append(["failure", key_ip, server_dict[key_ip]._timeout_date, "No data"])

        if server_dict[key_ip]._is_overload:
            parsing_results.append(["overload", key_ip, server_dict[key_ip]._overload_date, "No data"])

    for key_ip in network_dict:
        if network_dict[key_ip]._is_subnet_failure:
            parsing_results.append(["subnet_error", key_ip, network_dict[key_ip]._subnet_failure_date, "No data"])

    # 解析結果を返す
    return parsing_results


def check_failure(log, ser_obj, input_value) -> Union[list[str, ipad.IPv4Address, datetime, datetime], None]:
    """
    過去の記録と照合し故障期間を算出する

    Args:
        log (Ping_log): ファイル一行分のログデータ
        ser_obj (Server): サーバー毎の記録を保持しているオブジェクト
    """
    is_timeout = log._res == "-"

    # 応答がタイムアウトしていた場合
    if is_timeout:

        # タイムアウトが確認された場合、その日時を記録しておく
        if ser_obj._timeout_counter == 0:
            ser_obj._timeout_date = log._date
            ser_obj._timeout_counter += 1

        else:
            ser_obj._timeout_counter += 1

    # 応答が正常な場合
    else:
        if ser_obj._timeout_counter == 0:
            pass

        # 前の応答結果がタイムアウトであった & タイムアウトの連続上限を超えていた場合
        elif ser_obj._timeout_counter >= input_value._N:

            # 解析結果をコピーして保持
            report = ["failure", deepcopy(log._ip), deepcopy(ser_obj._timeout_date), deepcopy(log._date)]

            # 復旧したサーバーは故障リストから外す
            ser_obj._timeout_counter = 0

            return report

        else:
            # 復旧したサーバーは故障リストから外す
            ser_obj._timeout_counter = 0
    return None


def check_overload(log, ser_obj, input_value) -> Union[list[str, ipad.IPv4Address, datetime, datetime], None]:
    """
    過去の記録と照合しサーバーの状態が過負荷であるかを算出する
    また、Serverオブジェクトの更新も行う

    Args:
        log (Ping_log): ファイル一行分のログデータ
        ser_obj (Server): サーバー毎の記録を保持しているオブジェクト
    """
    ser_obj.update_que(log._res)

    # 負荷の値を取得
    load = ser_obj.calc_load()

    # 直近にタイムアウトが含まれる or 負荷の値が過負荷に相当する場合
    if load == -1 or load > input_value._T:

        # 既に過負荷であるとの記録がなければオブジェクトを更新
        if not ser_obj._is_overload:
            ser_obj._is_overload = True
            ser_obj._overload_date = log._date

    # 負荷が正常値の場合
    elif ser_obj._is_overload:
        ser_obj._is_overload = False

        # 解析結果をコピーして保持
        report = ["overload", deepcopy(log._ip), deepcopy(ser_obj._overload_date), deepcopy(log._date)]
        return report

    return None


def check_subnet_failure(log, ser_dict, sbn_obj) -> Union[list[str, ipad.IPv4Address, datetime, datetime], None]:
    """
    サブネット内のサーバー全体が故障しているかを確認する
    全体が故障していた場合サブネット内のサーバーどれか一つが復旧するまでの期間を記録する

    Args:
        log (Ping_log): ファイル一行分のログデータ
        ser_dict (Dict[str,Server]): Serverオブジェクトを保持しているdict
        sbn_obj (Subnet): サブネット単位での記録を保持しているオブジェクト

    """
    is_timeout = log._res == "-"

    # 応答がタイムアウトしていた場合
    if is_timeout:
        for server in sbn_obj._server_list:
            # 他にタイムアウトしていないサーバーが一つでもあればbreak
            if not ser_dict[server].is_server_timeout():
                break
        else:
            # サブネットの全てのサーバーがタイムアウトしているとき
            sbn_obj._is_subnet_failure = True
            sbn_obj.record_failure_date(log._date)
    else:
        # 応答も他サーバーも正常な場合
        if not sbn_obj._is_subnet_failure:
            pass

        # サブネット内の異常が復旧した場合
        else:
            sbn_obj._is_subnet_failure = False
            report = [
                "subnet_error",
                deepcopy(sbn_obj._subnet),
                deepcopy(sbn_obj._subnet_failure_date),
                deepcopy(log._date),
            ]
            return report
    return None


def get_network_address(ip):
    """
    ipアドレスをIPv4Networkオブジェクトに変換しネットワークアドレスを返す

    """
    network = ipad.IPv4Network(ip, strict=False)
    return network


def get_ipadress_obj(ip):
    """
    ipアドレスをIPv4Networkオブジェクトに変換する

    """
    ip_obj = ipad.ip_interface(ip)
    return ip_obj


def output_results(results: list[list[str, str, datetime, datetime]]) -> None:
    """
    解析結果を読み出し出力用のメソッドへ渡す
    結果がNoneであった場合は渡さない

    """
    for report in results:
        if report is not None:

            # サーバーの状態、アドレス、故障日時、復旧日時に分割
            report_value = (v for v in report)

            status = next(report_value)
            ip = next(report_value)
            found_date = next(report_value)
            recovery_date = next(report_value)

            # 出力する
            output_report(status, ip, found_date, recovery_date)


def output_report(status, ip, found_date, recovery_date) -> None:
    """
    異常が発生した期間を出力するメソッド

    Args:
        ip (str): サーバーのアドレス
        found_date (datetime): 異常が確認された日時
        recovery_date (datetime): 異常からの復旧が確認された日時
    """

    print(":{:<15}:{:<17}:{:<22}:{:<10}".format(status, str(ip), str(found_date), str(recovery_date)))


def main():
    FILE_PATH = "log.txt"

    # パラメータの設定
    input_value = init_param()

    # ファイルデータの読み取り
    log_list: list[Ping_log] = read_ping_log(FILE_PATH)

    # ログを解析し結果を取得
    results = parse_log(log_list, input_value)

    # ヘッダー出力
    print("")
    output_report("status", "address", "failure found", "confirm recovery")
    print("")

    # 解析結果の出力
    output_results(results)


main()
