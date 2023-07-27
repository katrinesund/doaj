import logging
import os
import sys

import pandas as pd
from gspread.utils import ValueInputOption

from portality.scripts.githubpri import pri_data_serv, gdrive_sheet_serv
from portality.scripts.githubpri.gdrive_sheet_serv import create_or_load_worksheet

log = logging.getLogger(__name__)


def priorities(priorities_file,
               gdrive_key_path=None,
               outfile=None,
               gdrive_filename=None,
               github_api_key=None,
               github_username=None,
               github_password=None, ):
    sender = pri_data_serv.GithubReqSender(api_key=github_api_key, username=github_username, password=github_password)
    user_pri_map = pri_data_serv.create_priorities_excel_data(priorities_file, sender)

    if outfile is not None:
        pd.concat({user: pri_df for user, pri_df in user_pri_map.items()}, axis=1).to_csv(outfile)

    print('[Start] update google sheet')

    if gdrive_filename is None:
        print('gdrive filename is not provided, skip updating google sheet')
        sys.exit(0)
    elif gdrive_key_path is None:
        log.warning('gdrive json key path is not provided, skip updating google sheet')
        sys.exit(1)

    display_df = pd.concat({user: pri_df.drop('issue_url', axis=1)
                            for user, pri_df in user_pri_map.items()},
                           axis=1)
    client = gdrive_sheet_serv.load_client(gdrive_key_path)
    sh = client.open(gdrive_filename)

    worksheet = create_or_load_worksheet(sh)

    gdrive_sheet_serv.update_sheet_by_df(worksheet, display_df)

    # assign title to issue_url's hyperlink
    cells = []
    for col_idx, (column_keys, titles) in enumerate(display_df.items()):
        if 'title' not in column_keys:
            continue
        username, *_ = column_keys
        titles = titles.dropna().apply(lambda x: x.replace('"', '""'))
        cells = worksheet.range(3, col_idx + 1, len(titles) + 3, col_idx + 1)
        for (row_idx, title), cell in zip(titles.items(), cells):
            link = user_pri_map[username].loc[row_idx, 'issue_url']
            cell.value = f'=HYPERLINK("{link}", "{title}")'
        worksheet.update_cells(cells, ValueInputOption.user_entered)

    gdrive_sheet_serv.apply_prilist_styles(worksheet, display_df)
    print('[End] update google sheet')


def main():
    """
    you need github and google drive api key to run this script
    DOAJ_GITHUB_KEY is github api key

    DOAJ_PRILIST_KEY_PATH is json file path for google drive api
    the DOAJ_PRILIST_KEY_PATH should be enabled for
    * 'google drive api'
    * 'google sheet api'

    """
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username",
                        help="github username")
    parser.add_argument("-p", "--password",
                        help="github password")
    parser.add_argument("-r", "--rules",
                        help="file path of rules excel")
    parser.add_argument("-o", "--out",
                        help="file path of local output excel")
    parser.add_argument("-g", "--gdrive-name",
                        help="excel name in google drive")

    args = parser.parse_args()


    priorities(args.rules,
               outfile=args.out,
               gdrive_filename=args.gdrive_name,
               gdrive_key_path=os.environ.get('DOAJ_PRILIST_KEY_PATH'),
               github_api_key=os.environ.get('DOAJ_GITHUB_KEY'),
               github_username=args.username,
               github_password=args.password,
               )


if __name__ == "__main__":
    main()
