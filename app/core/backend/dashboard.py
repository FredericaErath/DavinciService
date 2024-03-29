from datetime import datetime
import pandas as pd
from dateutil.relativedelta import relativedelta

from app.constant import PRICE_MAP
from app.core.backend.surgery import get_surgery_by_tds
from app.core.database import user, surgery, apparatus, supplies
from app.core.database.message import get_message


def get_detail_count(df, name: str):
    """Helper function to get instrument or consumables time series info"""

    def _get_instrument(x):
        dict_x = x[f"{name}_detail"]
        dict_x["date"] = x["date"][0:7]
        return dict_x

    df = df[[f"{name}_detail", "date"]].explode(f"{name}_detail")
    df[f"{name}_detail"] = df.apply(lambda x: _get_instrument(x), axis=1)
    df = pd.DataFrame(df[f"{name}_detail"].tolist())
    if name == "instruments":
        group_by_key = ["date", "id"]
    else:
        group_by_key = ["date", "name"]
    count = df.groupby(group_by_key).count()["description"].reset_index().rename(
        columns={"description": "count"})
    count = count.merge(
        df[["id", "name", "description", "date"]],
        on=group_by_key, validate="m:m", how="left").drop_duplicates(subset=group_by_key).sort_values(["name", "id"])

    accident_count = df[df["description"] != "默认"]
    if len(accident_count) != 0:
        accident_group = accident_count.groupby(group_by_key).count()[
            "description"].reset_index().rename(
            columns={"description": "count"})
        accident_count = accident_count[["id", "name", "description", "date"]].merge(
            accident_group,
            on=group_by_key, validate="m:m", how="left").sort_values(["name", "id"])
    else:
        accident_count = []
    return count, accident_count


def get_doctor_contribution(df: list, name: str):
    """Helper functions to get doctor's daily contributions"""
    df = pd.DataFrame(df)
    df = df[df["chief_surgeon"] == name].groupby(["date"]).count()["p_name"].reset_index().rename(
        columns={"p_name": "count"})
    return df.to_dict("records")


def get_time_series(df, name: str):
    """Helper function to get instrument or consumables time series"""
    x_axis = df["date"].drop_duplicates().sort_values()
    data = []
    legend = []
    if name == "instruments":
        series = df[["name", "count", "date", "id"]]
        for key, value in series.groupby(["id"]):
            value = value.merge(x_axis, on="date", how="outer").sort_values("date").fillna(0)
            name = f"{key[0]}号{value['name'][0]}"
            legend.append(name)
            data.append({"name": name, "data": value["count"].tolist(), "type": "line"})
    if name == "consumables":
        series = df[["name", "count", "date"]]
        for key, value in series.groupby(["name"]):
            value = value.merge(x_axis, on="date", how="outer").drop_duplicates("date").sort_values("date").fillna(0)
            name = key[0]
            legend.append(name)
            data.append({"name": name, "data": value["count"].tolist(), "type": "line"})
    return {"xAxis": x_axis.tolist(), "series": data, "legend": legend}


def get_benefit_analysis(df):
    """
    Helper function to get benefit analysis data
    """

    def _format(num):
        return "%.2f" % float(num)

    def calculate_price(x):
        instruments = x["instruments"].split(',')
        consumables = x["consumables"].split(',')
        i_sum = 0
        for i in instruments:
            i_sum += PRICE_MAP[i]
        for j in consumables:
            i_sum += PRICE_MAP[j]
        return i_sum

    df["sum"] = df.apply(lambda x: calculate_price(x[["instruments", "consumables"]]), axis=1)
    df["real_sum"] = 33000
    df["gap"] = df["real_sum"] - df["sum"]
    sum_all = {"total_cost": _format(df["sum"].sum()), "total_paid": _format(df["real_sum"].sum()),
               "total_gap": _format(df["gap"].sum())}
    df["sum"] = df["sum"].apply(lambda x: format(x, '.2f'))
    df["gap"] = df["gap"].apply(lambda x: format(x, '.2f'))
    return df[["p_name", "date", "admission_number", "department", "s_name", "chief_surgeon", "instruments",
               "consumables", "sum", "real_sum", "gap"]], sum_all


def get_surgery_dashboard(begin_time: datetime = None, end_time: datetime = None):
    # By default, the data of the past year is obtained
    if begin_time is None and end_time is None:
        end_time = datetime.now()
        begin_time = end_time - relativedelta(years=1)

    df = pd.DataFrame(get_surgery_by_tds(begin_time=begin_time, end_time=end_time))
    if len(df) == 0:
        return {"surgeon_count": [], "nurse_count": [], "department_count": [], "top_ten": [[], []],
                "instrument_count": [], "accident_instrument_count": [], "consumable_count": [],
                "accident_consumable_count": [], "instrument_time_series": [], "instrument_acc_time_series": [],
                "consumable_time_series": [], "consumable_acc_time_series": [], "df_benefits": [], "sum_all": []}

    # get surgeon and department count
    surgeon_count = df.groupby(["department",
                                "chief_surgeon"]).count()["p_name"].reset_index().rename(columns={"p_name": "c_count"})
    grouped = surgeon_count.groupby(["department"])["c_count"].sum().reset_index().rename(
        columns={"c_count": "d_count"})
    surgeon_count = surgeon_count.merge(grouped, how="left", on="department", validate="m:1")
    department_count = surgeon_count[["department", "d_count"]].drop_duplicates().rename(
        columns={"department": "name", "d_count": "value"})

    # get nurse count
    df_instrument = df.apply(lambda x: x["instrument_nurse"].split(','), axis=1).explode().reset_index()
    df_circulate = df.apply(lambda x: x["circulating_nurse"].split(','), axis=1).explode().reset_index()
    df_circulate = df_circulate.groupby([0]).count()["index"].reset_index().rename(
        columns={0: "name", "index": "count"})
    df_instrument = df_instrument.groupby([0]).count()["index"].reset_index().rename(
        columns={0: "name", "index": "count"})
    df_nurse = df_circulate.merge(df_instrument, how="outer", on="name", validate="1:1").fillna(0).rename(
        columns={"count_x": "count_circulate", "count_y": "count_instrument"})
    df_nurse["sum"] = df_nurse["count_circulate"] + df_nurse["count_instrument"]

    # get top 10 surgeon
    if len(df) < 10:
        df_top_ten = surgeon_count.sort_values("c_count")[["chief_surgeon", "c_count"]]
    else:
        df_top_ten = surgeon_count.sort_values("c_count")[["chief_surgeon", "c_count"]][:10]

    # get count
    instrument_count, accident_instrument_count = get_detail_count(df, "instruments")
    consumable_count, accident_consumable_count = get_detail_count(df, "consumables")

    # get time series
    instrument_time_series = get_time_series(instrument_count, "instruments")
    instrument_accident_time_series = get_time_series(accident_instrument_count, "instruments")
    consumable_time_series = get_time_series(consumable_count, "consumables")
    consumable_accident_time_series = get_time_series(accident_consumable_count, "consumables")

    # get benefit analysis
    df_benefits, sum_all = get_benefit_analysis(df)

    return {"df": df[["chief_surgeon", "date", "p_name"]].to_dict('records'),
            "surgeon_count": surgeon_count.to_dict('records'),
            "nurse_count": df_nurse.to_dict('records'), "department_count": department_count.to_dict('records'),
            "top_ten": [df_top_ten["c_count"].tolist(), df_top_ten["chief_surgeon"].tolist()],
            "instrument_count": instrument_count.to_dict('records'),
            "accident_instrument_count": accident_instrument_count.to_dict('records'),
            "consumable_count": consumable_count.to_dict('records'),
            "accident_consumable_count": accident_consumable_count.to_dict('records'),
            "instrument_time_series": instrument_time_series,
            "instrument_acc_time_series": instrument_accident_time_series,
            "consumable_time_series": consumable_time_series,
            "consumable_acc_time_series": consumable_accident_time_series,
            "df_benefits": df_benefits.to_dict('records'), "sum_all": sum_all}


def get_general_data():
    """
    Count collection lengths of users, surgery, apparatus, supply
    :return: dict of lengths of collections
    """
    users = user.count_documents({})
    surgeries = surgery.count_documents({})
    instrument = apparatus.count_documents({})
    consumable = supplies.count_documents({})
    end_time = datetime.now()
    begin_time = end_time.replace(day=1, hour=0, minute=0, second=0)
    df = pd.DataFrame(get_surgery_by_tds(begin_time=begin_time, end_time=end_time))
    if len(df) != 0:
        df, sum_all = get_benefit_analysis(df)
        if len(sum_all) != 0:
            sum_all = sum_all["total_cost"]
        else:
            sum_all = 0
    else:
        sum_all = 0
    message = pd.DataFrame(get_message(begin_time=begin_time, end_time=end_time))
    if len(message) != 0:
        unhandled_message = len(message[message["status"] == 1]) / len(message) * 100
        message = str(len(message)) + '条'
    else:
        message = "本月无消息"
        unhandled_message = 0
    return {"users": str(users), "surgery": str(surgeries), "instrument": str(instrument),
            "consumable": str(consumable), "cost": sum_all, "message": message,
            "unhandled_message": unhandled_message}
