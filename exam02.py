# 設問１
from datetime import datetime
from typing import Dict


class Ping_log:
    """
    ログを管理するオブジェクト
    ログの日付、アドレス、応答結果を管理する
    """

    def __init__(self, f_line) -> None:
        # 一行分のログを日付、アドレス、応答結果に分割
        str_date, str_ip, str_res = map(str, f_line.split(","))

        # オブジェクトとして保持
        self._date = datetime.strptime(str_date, "%Y%m%d%H%M%S")
        self._address = str_ip
        self._res = str_res.replace("\n", "")


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


def check_failure(log_list: list[Ping_log], input_value) -> None:
    """
    ログから故障記録を読みだすメソッド

    Args:
        log_list (list[Ping_log]): 監視ログを保持しているリスト
    """
    print("{:<9}:{:<16}:{:<22}{:<10}".format("", "address", "failure found", "confirm recovery"))
    COUNT_DEF = 1
    DATE_INDEX = 0
    COUNT_INDEX = 1

    # 故障しているサーバーを記録するdict
    failure_server_dict: Dict[str, list[datetime, int]] = {}  # key:サーバーのアドレス, value:故障発見時の日時とタイムアウトの回数

    for log in log_list:
        is_timeout = log._res == "-"

        # 応答がタイムアウトしていた場合
        if is_timeout:

            # タイムアウトが確認された場合、その日時を記録しておく
            if log._address not in failure_server_dict:
                failure_server_dict[log._address] = [log._date, COUNT_DEF]

            #
            else:
                failure_server_dict[log._address][COUNT_INDEX] += 1

        # 応答が正常な場合
        else:
            if log._address not in failure_server_dict:
                pass

            # 故障リストに載っていてかつタイムアウトの連続上限を超えていた場合
            elif failure_server_dict[log._address][COUNT_INDEX] >= input_value.N:

                # アドレスと期間を出力する
                output_failure_report(log._address, failure_server_dict[log._address][DATE_INDEX], log._date)

                # 復旧したサーバーは故障リストから外す
                del failure_server_dict[log._address]
            else:
                # 復旧したサーバーは故障リストから外す
                del failure_server_dict[log._address]

    # ログ上で復旧していないサーバーの故障記録を出力
    for key in failure_server_dict:
        if failure_server_dict[log._address][COUNT_INDEX] >= input_value.N:
            output_failure_report(key, failure_server_dict[key][DATE_INDEX], "No data")


def output_failure_report(address, failure_date, recovery_date) -> None:
    """
    故障期間を出力するメソッド

    Args:
        address (str): サーバーのアドレス
        failure_date (datetime): 故障が確認された日時
        recovery_date (datetime): 故障からの復旧が確認された日時
    """

    print("{:<9}:{:<16}:{:<22}{:<10}".format("failure", address, str(failure_date), str(recovery_date)))


class init_param:
    """
    入力されるパラメータを管理するオブジェクト
    """

    N: int

    def __init__(self) -> None:
        print("N回以上連続してタイムアウトした場合にのみ故障とみなします")
        print("Nの値を入力してください")
        self.N = int(input())


def main():
    FILE_PATH = "log04.txt"

    # パラメータの設定
    input_value = init_param()

    # ファイルデータの読み取り
    log_list: list[Ping_log] = read_ping_log(FILE_PATH)

    # 故障記録の出力
    check_failure(log_list, input_value)


main()
