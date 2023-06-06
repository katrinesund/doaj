import pandas as pd
import argparse
from portality import models
from portality.crosswalks.journal_form import JournalFormXWalk

"""
This script is the second step of generating csv file with the details validity of the urls in the journal.
First step is to execute 'journal_urls' script.
Execute this by passing required input files to generate a report of the urls along with journals information.

Steps to generate the report csv file:

1. Run journal_urls.py -> python portality/scripts/journal_urls.py
2. The above scripts will generate doaj_journals_links.csv file at the location mention in the config for 
   'STORE_LOCAL_DIR'. Example location 'local_store/main/doaj_journals_links.csv'
3. This script also generates the HTML files at the location from where the script is executed
4. Input the html files to link checker tool (https://www.drlinkcheck.com/)  by copying the html files to the server and mention the location to the 
   link checker tool
5. Run the link check on the tool and export the csv file to a local location
6. Run link_checker_report.py by passing the file locations as parameters.
   ex: python portality/scripts/link_checker_report.py --file <links-doaj-link-check-test-2023-05-11_13-31-59.csv>
    --journal_csv_file <local_store/main/doaj_journals_links.csv>
    Provide the absolute paths for the files
7. Once the above script is run, final report csv file will be generated 
"""


def write_results(df, filename='multi_result.csv'):
    """
    Write results to a csv file
    :param df: DataFrame object of the csv file
    :param filename: Output file name
    :return:
    """
    # Sort the results by the original index
    df_sorted = df.sort_values(by='Journal title')

    df_sorted.to_csv(filename, index=False)

    print("Result CSV file has been written.")


def _get_link_type(link, journal):
    form = JournalFormXWalk.obj2form(journal)

    locations = []
    subs = []
    for k, v in form.items():
        if v is None:
            continue
        if isinstance(v, list):
            if link in v:
                locations.append(k)
            else:
                for e in v:
                    if isinstance(e, dict):
                        for sk, sv in e.items():
                            if not isinstance(sv, str):
                                continue
                            if link == sv:
                                locations.append(sk)
                            elif sv.startswith(link):
                                subs.append(sk)
                    else:
                        if e.startswith(link):
                            subs.append(k)
                            break
        else:
            if not isinstance(v, str):
                continue
            if v == link:
                locations.append(k)
            elif v.startswith(link):
                subs.append(k)

    return locations + subs


def fetch_matching_rows(df, report_values):
    """Check with journals dataframe and retrieve matching rows with url.
       :param df: DataFrame
       :param report_values: url to match
       :return: DataFrame with matching rows
    """
    # Search for the text in the entire csv file
    mask = df.applymap(lambda x: report_values["url"] in str(x))

    # Get the rows where the text is found
    df_result = df[mask.any(axis=1)]

    if not df_result.empty:
        columns = ['Journal title', 'Added on Date', 'Last updated Date', "Journal ID"]

        # Select the desired columns from the DataFrame
        df_result_selected_columns = df_result[columns].copy()  # create a copy to avoid SettingWithCopyWarning

        jid = df_result_selected_columns["Journal ID"].values[0]
        journal = models.Journal.pull(jid)
        primary_type = ""
        question_link = ""
        types = []

        if journal is not None:
            types = _get_link_type(report_values["url"], journal)
            if len(types) > 0:
                primary_type = types[0]
                question_link = "https://doaj.org/admin/journal/" + jid + "#question-" + primary_type

        # Add more columns to the DataFrame
        df_result_selected_columns["DOAJ Form"] = "https://doaj.org/admin/journal/" + jid
        df_result_selected_columns["Form Field"] = question_link
        df_result_selected_columns['Url'] = report_values["url"]
        df_result_selected_columns['Type'] = primary_type
        df_result_selected_columns["Also present in"] = ", ".join(types)
        df_result_selected_columns['BrokenCheck'] = report_values["broken_check"]
        df_result_selected_columns['RedirectUrl'] = report_values["redirect_url"]
        df_result_selected_columns['RedirectType'] = report_values["redirect_type"]

        return df_result_selected_columns
    else:
        return pd.DataFrame()


def check_links(df, journal_df):
    """
    Retrieve the URLs from the csv file
    :param df: DataFrame object of the csv file which is exported from link checker tool
    :param journal_df: DataFrame object of the journals csv file generated by journal_urls.py script
    :return: DataFrame object of the results
    """
    results = []

    # Iterate through the rows of the DataFrame
    for index, row in df.iterrows():

        values = {
            'url': row["Url"],
            'broken_check': row["BrokenCheck"],
            'redirect_url': row["RedirectUrl"],
            'redirect_type': row["RedirectType"]
        }

        result = fetch_matching_rows(journal_df, values)
        if not result.empty:
            results.append(result)

    return pd.concat(results) if results else pd.DataFrame()


def generate_report(csv_file, journal_csv_file):
    """
    Generate a report in a format that is useful to analyze from the csv file exported from link checker tool
    :param csv_file: csv file exported from link checker tool
    :param journal_csv_file: journal csv file generated by the journal_urls.py script
    :return:
    """
    df = pd.read_csv(csv_file)
    journal_df = pd.read_csv(journal_csv_file)
    df = check_links(df, journal_df)
    write_results(df)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    # Add arguments
    parser.add_argument('--file', help='Specify csv file location downloaded from link checker tool')
    parser.add_argument('--journal_csv_file', help='Specify the journal csv file location generated by journal_urls.py'
                                                   ' script')

    # Parse command-line arguments
    args = parser.parse_args()

    generate_report(args.file, args.journal_csv_file)
