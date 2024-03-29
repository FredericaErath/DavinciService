import os
from typing import Union

from fastapi import APIRouter, UploadFile, Depends
from fastapi.responses import FileResponse
from starlette.background import BackgroundTasks

from app.core.backend.administrator import delete_user_by_uid, add_users_by_file, get_users, update_message_by_mid, \
    get_message_by_filter, delete_message_by_mid
from app.core.backend.dashboard import get_surgery_dashboard, get_doctor_contribution, get_general_data
from app.core.backend.instrument import get_all_instrument, revise_instrument, add_instruments_by_file, \
    add_one_instrument, download_instrument_qr_code, delete_instruments_by_id, get_instrument_general
from app.core.backend.supply import get_supply_general, insert_supplies, delete_supply_by_id, update_supply_description
from app.core.backend.surgery import get_surgery_by_tds, update_surgery_info, insert_surgery_admin
from app.core.backend.user import register, revise_user_info, auth
from app.model.doctor import Message
from app.model.instrument import Instrument
from app.model.surgery import SurgeryGet, SurgeryUpdate, Contribution
from app.model.supply import Supply, SupplyGet, SupplyRevise
from app.model.user import User

router = APIRouter(prefix="/admin")


@router.post('/add_user', tags=['Admin'])
def add_user(user: User):
    return register(u_id=user.u_id, name=user.name, user_type=user.user_type, pwd=user.pwd)


@router.post('/revise_user', tags=['Admin'])
def revise_user(user: User):
    return revise_user_info(u_id=user.u_id, pwd=user.pwd, name=user.name, new_u_id=user.new_id)


@router.post('/get_user', tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def get_users_api(user: User):
    return get_users(u_id=user.u_id, user_type=user.user_type, name=user.name)


@router.post('/delete_user', tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def delete_user_api(u_id: Union[list, str]):
    return delete_user_by_uid(u_id=u_id)


@router.post("/upload_users", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
async def upload_users(file: UploadFile):
    file_upload = await file.read()
    file_name = 'temp.xlsx'
    f_out = open(f'{file_name}', 'xb')
    f_out.write(file_upload)
    res = add_users_by_file(file_name)
    f_out.close()
    task = BackgroundTasks()
    task.add_task(os.remove(file_name), file_name)
    return res


@router.get("/get_instruments", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def get_instrument_api():
    return get_all_instrument()


@router.post("/get_specific_instruments", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def get_instrument(instrument: Instrument):
    return get_instrument_general(begin_time=instrument.begin_time, end_time=instrument.end_time,
                                  times=instrument.times, i_id=instrument.i_id,
                                  i_name=instrument.i_name, validity=instrument.validity)


@router.post("/revise_instruments", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def revise_instrument_api(instrument: Instrument):
    return revise_instrument(i_id=instrument.i_id, times=instrument.times)


@router.post("/add_instrument", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def add_instrument(instrument: Instrument):
    res = add_one_instrument(i_name=instrument.i_name, times=instrument.times)
    response = FileResponse(res["file"], filename=res["file_name"], headers={"Access-Control-Expose-Headers":
                                                                                 "content-disposition"})
    return response


@router.post("/upload_instruments", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
async def upload_instruments(file: UploadFile):
    file_upload = await file.read()
    file_name = 'temp.xlsx'
    f_out = open(f'{file_name}', 'xb')
    f_out.write(file_upload)
    res = add_instruments_by_file(file_name)
    f_out.close()
    task = BackgroundTasks()
    task.add_task(os.remove(file_name), file_name)
    return FileResponse(res)


@router.post("/delete_instruments", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def delete_instruments(instrument: Instrument):
    res = delete_instruments_by_id(i_id=instrument.i_id)
    return res


@router.post("/download_instrument_qrcode", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def download_qrcode(instrument: Instrument):
    res = download_instrument_qr_code(i_id=instrument.i_id)
    response = FileResponse(res, filename=f"{str(instrument.i_id)}.png", headers={"Access-Control-Expose-Headers":
                                                                                  "content-disposition"})
    return response


@router.post('/get_surgery', tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def get_surgery_api(surgery: Union[SurgeryGet, None]):
    return get_surgery_by_tds(page=surgery.page, limit_size=surgery.limit_size,
                              begin_time=surgery.begin_time, end_time=surgery.end_time,
                              department=surgery.department, s_name=surgery.s_name)


@router.post('/update_surgery', tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def update_surgery_api(surgery: Union[SurgeryUpdate, None]):
    return update_surgery_info(s_id=surgery.s_id,
                               p_name=surgery.p_name,
                               begin_time=surgery.begin_time,
                               date=surgery.date,
                               admission_number=surgery.admission_number,
                               end_time=surgery.end_time,
                               department=surgery.department,
                               s_name=surgery.s_name,
                               chief_surgeon=surgery.chief_surgeon,
                               associate_surgeon=surgery.associate_surgeon,
                               instrument_nurse=surgery.instrument_nurse,
                               circulating_nurse=surgery.circulating_nurse,
                               instruments=surgery.instruments,
                               consumables=surgery.consumables)


@router.post("/insert_surgery_admin", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def insert_surgery(surgery: SurgeryUpdate):
    return insert_surgery_admin(begin_time=surgery.begin_time, end_time=surgery.end_time, p_name=surgery.p_name,
                                date=surgery.date, admission_number=surgery.admission_number,
                                department=surgery.department, s_name=surgery.s_name,
                                chief_surgeon=surgery.chief_surgeon, associate_surgeon=surgery.associate_surgeon,
                                instrument_nurse=surgery.instrument_nurse, circulating_nurse=surgery.circulating_nurse,
                                instruments=surgery.instruments, consumables=surgery.consumables)


@router.post('/get_supply', tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def get_supply_api(supply: Union[Supply, None]):
    return get_supply_general(begin_time=supply.begin_time, end_time=supply.end_time,
                              c_id=supply.c_id, c_name=supply.c_name,
                              description=supply.description, validity=supply.validity)


@router.post("/insert_supply", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def insert_supply_api(supply: SupplyGet):
    return insert_supplies(c_name=supply.c_name, num=supply.num)


@router.post("/delete_supply", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def delete_supply_api(c_id: Union[int, list[int]]):
    return delete_supply_by_id(c_id=c_id)


@router.post("/revise_supply", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def revise_supply(supply: SupplyRevise):
    return update_supply_description(c_id=supply.c_id, description=supply.description)


@router.post("/get_surgery_dashboard", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def get_surgery_dashboard_api(supply: Supply):
    return get_surgery_dashboard(begin_time=supply.begin_time, end_time=supply.end_time)


@router.post("/get_doctor_contribution", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def get_doctor_contribution_api(contribution: Contribution):
    return get_doctor_contribution(df=contribution.df, name=contribution.name)


@router.post("/get_message", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def get_message(message: Message):
    return get_message_by_filter(status=message.status, priority=message.priority,
                                 begin_time=message.begin_time, end_time=message.end_time)


@router.post("/update_message", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def update_message(message: Message):
    return update_message_by_mid(m_id=message.m_id, status=message.status,
                                 priority=message.priority, feedback=message.feedback)


@router.post("/delete_message", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def delete_message(message: Message):
    return delete_message_by_mid(m_id=message.m_id)


@router.post("/get_general_data", tags=['Admin'], dependencies=[Depends(auth.decode_token)])
def get_general():
    return get_general_data()
