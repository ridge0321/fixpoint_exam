# 設問１
from datetime import datetime
from collections import deque
from typing import Dict


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


def parse_log(log_list: list[Ping_log], input_value) -> None:
    """
    Ping_log型に加工したログを読み込む

    Args:
        log_list (list[Ping_log]): 監視ログを保持しているリスト
    """

    server_dict: Dict[str, Server] = {}  # key:サーバーのアドレス, value:Serverオブジェクト

    # ログを一行分ずつ解析
    for log in log_list:

        # 各サーバーごとにServerオブジェクトを作成
        if log._address not in server_dict:
            server_dict[log._address] = Server(input_value._M)

        # 故障期間の記録と解析
        check_failure(log, server_dict[log._address], input_value)
        # 過負荷の記録と解析
        check_overload(log, server_dict[log._address], input_value)

    # ログ上で復旧していないサーバーの記録を出力
    for key in server_dict:
        if server_dict[key]._timeout_counter >= input_value._N:
            output_report("failure", key, server_dict[key]._timeout_date, "No data")
        if server_dict[key]._is_overload:
            output_report("overload", key, server_dict[key]._overload_date, "No data")


def check_failure(log, ser_obj, input_value) -> None:
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

            # アドレスと期間を出力する
            output_report("failure", log._address, ser_obj._timeout_date, log._date)

            # 復旧したサーバーは故障リストから外す
            ser_obj._timeout_counter = 0
        else:
            # 復旧したサーバーは故障リストから外す
            ser_obj._timeout_counter = 0


def check_overload(log, ser_obj, input_value) -> None:
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

        # 過負荷を検知した日時～過負荷の解消を検知した日時までを出力
        output_report("overload", log._address, ser_obj._overload_date, log._date)


def output_report(status, address, found_date, recovery_date) -> None:
    """
    異常が発生した期間を出力するメソッド

    Args:
        address (str): サーバーのアドレス
        found_date (datetime): 異常が確認された日時
        recovery_date (datetime): 異常からの復旧が確認された日時
    """

    print("{:<9}:{:<16}:{:<22}{:<10}".format(status, address, str(found_date), str(recovery_date)))


def main():
    # FILE_PATH = "log_exam03_03.txt"
    FILE_PATH = "log05.txt"

    # パラメータの設定
    input_value = init_param()

    # ファイルデータの読み取り
    log_list: list[Ping_log] = read_ping_log(FILE_PATH)

    # 記録の解析と出力
    print("{:<9}:{:<16}:{:<22}{:<10}".format("", "address", "failure found", "confirm recovery"))
    parse_log(log_list, input_value)


main()
