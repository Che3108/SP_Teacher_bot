#!/usr/local/bin/python3.10
import gspread

gc = gspread.service_account()
main_dict = dict()

sh = gc.open("for bot")
worksheets = sh.worksheets()
worksheets_title = [i.title for i in worksheets]
main_dict['groups'] = dict()

for i in worksheets_title[1:]:
    l = sh.worksheet(i).get_all_values()
    main_dict['groups'].update({i:{'students':l[0][1:], 'records': len(l)}})

worksheet = sh.worksheet(worksheets_title[0])

list_of_dicts = worksheet.get_all_records()
for k in list_of_dicts[0].keys():
    main_dict.update({k:[]})
for i in list_of_dicts:
    for k, v in i.items():
        if v != '':
            main_dict[k] += [v]
print(main_dict)
