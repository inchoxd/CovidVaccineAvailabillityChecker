import os
import sys
import json
import requests
from dotenv import load_dotenv

import pytz
from datetime import datetime as dt


class CheckVaccine:
    def __init__(self):
        load_dotenv(override=True)
        self.base_uri = os.environ['BASEURI']


    def _open_json(self):
        with open('areaId.json', 'r') as f:
            area_ids = json.loads(f.read())

        return area_ids


    def can_reserve_date(self, city_code, available, date_after, date_before):
        uri = f'{self.base_uri}/{city_code}/reservation_frame/?department_id={available}&item_id=1&start_date_after={date_after}&start_date_before={date_before}'
        r = requests.get(url=uri)
        r_json = r.json()

        reserve_info = r_json['reservation_frame']
        l_rtn_data = list()
        for info_data in reserve_info:
            tmp_start_at = info_data['start_at']
            tmp_end_at = info_data['end_at']
            start_at = dt.fromisoformat(tmp_start_at).strftime('%m/%d %H:%M')
            end_at = dt.fromisoformat(tmp_end_at).strftime('%H:%M')
            reservation_cnt = info_data['reservation_cnt']
            reservation_cnt_limit = info_data['reservation_cnt_limit']
            reservation_remain = str(int(reservation_cnt_limit-reservation_cnt))

            if int(reservation_remain) > 0:
                rtn_data = {
                        'date':f'{start_at}~{end_at}',
                        'limit':reservation_cnt_limit,
                        'remain':reservation_remain
                        }
                l_rtn_data.append(rtn_data)

        return l_rtn_data


    def get_available_date(self, city_code, department_id, item_id):
        l_available_date = list()
        dt_now = dt.now(pytz.timezone('Asia/Tokyo'))
        year = dt_now.strftime('%Y')
        month = dt_now.strftime('%m')
        uri = f'{self.base_uri}/{city_code}/available_date/?department_id={department_id}&item_id={item_id}&year={year}&month={month}'
        r = requests.get(url=uri)

        if r.text != '':
            cu_available_date = r.json()
            for date in cu_available_date:
                if cu_available_date[date]['available'] != False:
                    total_cnt = cu_available_date[date]['total_cnt']
                    total_cnt_limit = cu_available_date[date]['total_cnt_limit']
                    remain = str(int(total_cnt_limit - total_cnt))

                    rtn_data = {
                            'date':date,
                            'limit':total_cnt_limit,
                            'remain':remain
                            }
                    l_available_date.append(rtn_data)

        return l_available_date


    def available_dept(self, city_code):
        try:
            uri = f'{self.base_uri}/{city_code}/available_department/'
            r = requests.get(url=uri)

            r_json = r.json()
            available = r_json['department_list']
        except KeyError:
            return 'Organization not found'

        return available


    def get_items(self, city_code):
        items = dict()
        uri = f'{self.base_uri}/{city_code}/item'
        r = requests.get(url=uri)
        r_json = r.json()
        
        for item in r_json['item']:
            items[int(item['id'])] = item['name']

        return items


    def get_department_info(self, city_code, available=None, vaccines=None):
        i = 0
        if not vaccines:
            vaccines = self.get_items(city_code)
            
        l_rtn_data = list()
        available_dept = list()
        uri = f'{self.base_uri}/{city_code}/department/'

        r = requests.get(url=uri)
        r_json = r.json()
        l_dept = r_json['department']

        for val in l_dept:
            dept_id = val['id']
            info = val['information']
            name = info['displayed_name']
            area = info['area']
            access = info['access']
            postcode = info['postcode']
            addr1 = info['address1']
            addr2 = info['address2']
            phone_number = info['phone_number']
            homepage = info['homepage']
            items = val['item']
            i = 0
            for item in items:
                items[i] = {
                        items[i]:vaccines[items[i]]
                        }
                i += 1

            rtn_data = {
                    'dept_id':dept_id,
                    'name':name,
                    'items':items,
                    'area':area,
                    'access':access,
                    'postcode':postcode,
                    'addr1':addr1,
                    'addr2':addr2,
                    'phone_number':phone_number,
                    'url':homepage
                    }

            if available != None:
                if dept_id in available:
                    l_rtn_data.append(rtn_data)
            else:
                l_rtn_data.append(rtn_data)

        return l_rtn_data


    def get_available_department(self, city_code):
        try:
            uri = f'{self.base_uri}/{city_code}/available_department/'
            r = requests.get(url=uri)

            r_json = r.json()
            available = r_json['department_list']

        except KeyError:
            raise KeyError()

        return available
    

    def can_reserve_departments(self, city_code, item_id, date_after, date_before):
        dept_info = None
        l_rtn_data = list()
        dept_available_data = list()
        uri = f'{self.base_uri}/{city_code}/reservation_frame/?item_id={item_id}&start_date_after={date_after}&start_date_before={date_before}'

        r = requests.get(url=uri)
        status_code = r.status_code

        if status_code == 200:
            r_json = r.json()
            departments = self.get_department_info(city_code)
            reservation_frame = r_json['reservation_frame']
            pre_dept_id = None

            iter_reservation_frame = iter(reservation_frame)
            next_dept_id = next(iter_reservation_frame)['department']

            for frame in reservation_frame:
                dept_id = frame['department']

                try:
                    next_dept_id = next(iter_reservation_frame)['department']

                except StopIteration:
                    next_dept_id = 'StopIteration'

                if dept_id != pre_dept_id:
                    dept_info = next((info for info in departments if info['dept_id'] == dept_id), None)

                    dept_available_data = list()
                    pre_dept_id = dept_id

                reservation_cnt = frame['reservation_cnt']
                reservation_cnt_limit = frame['reservation_cnt_limit']
                reservation_remain = reservation_cnt_limit - reservation_cnt

                if reservation_remain > 0:
                    available_data = {
                            'start_at':frame['start_at'],
                            'end_at':frame['end_at'],
                            'reservation_cnt':reservation_cnt,
                            'reservation_cnt_limit':reservation_cnt_limit,
                            'reservation_remain':reservation_remain
                            }
                    dept_available_data.append(available_data)
                    dept_info['availables'] = dept_available_data

                    if next_dept_id != dept_id:
                        l_rtn_data.append(dept_info)
            return l_rtn_data


    def get_city_code(self, prefecture, area):
        area_ids = self._open_json()
        data = area_ids['data']
        for pre_data in data:
            if prefecture in pre_data.keys():
                for area_info in pre_data[prefecture]:
                    if area in area_info.keys():
                        city_code = area_info[area]['id']

        return city_code
