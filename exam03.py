# 設問3
from datetime import datetime
from collections import deque
from typing import Dict, Union
from copy import deepcopy


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

        # オブジェクトとして保持
        self._date = datetime.strptime(str_date, "%Y%m%d%H%M%S")
        self._address = str_ip
        self._res = str_res.replace("\n", "")


class Server:
    """
    各サーバーアドレスごとに値を保持するためのクラス
    """

    def __init__(self, M) -> None:
        self._res_que = deque()  # 直近の応答を格納するque
        self._timeout_counter: int = 0
        self._timeout_date: datetime
        self._overload_date: datetime
        self._is_overload: bool = False
        self._M = M

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


def parse_log(log_list: list[Ping_log], input_value) -> list[list[str, str, datetime, datetime]]:
    """
    Ping_log型に加工したログを読み込む

    Args:
        log_list (list[Ping_log]): 監視ログを保持しているリスト
    """

    server_dict: Dict[str, Server] = {}  # key:サーバーのアドレス, value:Serverオブジェクト
    parsing_results: list[list[str, str, datetime, datetime]] = []  # 解析結果を保持するためのリスト

    # ログを一行分ずつ解析
    for log in log_list:

        # 各サーバーごとにServerオブジェクトを作成
        if log._address not in server_dict:
            server_dict[log._address] = Server(input_value._M)

        # 故障期間の記録を取得
        parsing_results.append(check_failure(log, server_dict[log._address], input_value))

        # 過負荷の記録を取得
        parsing_results.append(check_overload(log, server_dict[log._address], input_value))

    # ログ上で復旧していないサーバーの記録を出力
    for key in server_dict:
        if server_dict[key]._timeout_counter >= input_value._N:
            parsing_results.append(["failure", key, server_dict[key]._timeout_date, "No data"])

        if server_dict[key]._is_overload:
            parsing_results.append(["overload", key, server_dict[key]._overload_date, "No data"])

    # 解析結果を返す
    return parsing_results


def check_failure(log, ser_obj, input_value) -> Union[list[str, str, datetime, datetime], None]:
    """
    過去の記録と照合し故障期間を算出する
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
            report = ["failure", deepcopy(log._address), deepcopy(ser_obj._timeout_date), deepcopy(log._date)]

            # 復旧したサーバーは故障リストから外す
            ser_obj._timeout_counter = 0

            return report

        else:
            # 復旧したサーバーは故障リストから外す
            ser_obj._timeout_counter = 0
    return None


def check_overload(log, ser_obj, input_value) -> Union[list[str, str, datetime, datetime], None]:
    """
    過去の記録と照合しサーバーの状態が過負荷であるかを算出する
    また、Serverオブジェクトの更新も行う
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
        report = ["overload", deepcopy(log._address), deepcopy(ser_obj._overload_date), deepcopy(log._date)]
        return report

    return None


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
            address = next(report_value)
            found_date = next(report_value)
            recovery_date = next(report_value)

            # 出力する
            output_report(status, address, found_date, recovery_date)


def output_report(status, address, found_date, recovery_date) -> None:
    """
    異常が発生した期間を出力するメソッド

    Args:
        address (str): サーバーのアドレス
        found_date (datetime): 異常が確認された日時
        recovery_date (datetime): 異常からの復旧が確認された日時
    """

    print(":{:<10}:{:<16}:{:<22}:{:<10}".format(status, address, str(found_date), str(recovery_date)))


def main():
    # FILE_PATH = "log_exam03_03.txt"
    FILE_PATH = "log05.txt"

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
