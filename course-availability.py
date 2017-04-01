import os
import platform
from bs4 import BeautifulSoup
import argparse
import requests
import numpy as np
import pandas as pd
import re
import json
from lxml import html
import time
import subprocess

base_url = 'https://courses.illinois.edu'

def semsoup2subj(semester_soup, queried_course):
    # find the table containing both subject code and subject
    subject_list_xml = semester_soup.find("table", id="term-dt").find("tbody")
    temp_subjCode = []
    temp_subj = []
    temp_href = []
    # get subject code and subject
    for row in subject_list_xml.find_all("tr"):
        # get subject code
        subjCode_xml = row.find("td")
        temp_subjCode.append(str.upper(' '.join(subjCode_xml.get_text().split())))
        # get subject name
        subj_xml = subjCode_xml.find_next_sibling("td")
        temp_subj.append(str.upper(' '.join(subj_xml.get_text().split())))

    # build a dataframe with subject information
    d = {"code": temp_subjCode, "subject": temp_subj}
    df_subject = pd.DataFrame(data=d)
    
    # build a dataframe with queried course information
    df_query = pd.DataFrame(data = queried_course, \
            columns=['query_subject', 'query_number'])
    # find related course and course number that corresponds to the queried courses
    df_query_subj = df_subject.merge(df_query, \
                    left_on='code', right_on='query_subject') \
                    .append( \
                    df_subject.merge(df_query, \
                    left_on='subject', right_on='query_subject'), \
                    ignore_index=True) \
                    .drop_duplicates() 
    # Drop replicated col: query_subject
    df_query_subj.drop('query_subject', axis=1, inplace=True)
    return df_query_subj

def courseSoup2Df(soup):
    """
        Input: soup: BeautifulSoup instance
        Return: a Dataframe with all course information on the page
    """
    # parse the webpage to grab the script element
    script_tag = soup.find(type='text/javascript')
    # parse the value of the sectionDataObj JavaScript variable 
    # to extract out the JSON data
    script_txt = script_tag.contents[0]

    # initialize course info lists
    sct= []
    day= []
    tme= []
    ins = []
    loc = []
    stat = []
    crn = []
    ty = []

    # extract each row by looking for each json object
    pattern = re.compile(r'(\{[^}]+\})')
    for match in re.finditer(pattern, script_txt):
        # convert this string into a JSON document
        json_txt = json.loads(match.group(0))

        # Use an XML parser directly to extract the text 
        # contents of the HTML element
        sct.append(parse_xml(json_txt, 'section'))
        day.append(parse_xml(json_txt, 'day'))
        tme.append(parse_xml(json_txt, 'time'))
        ins.append(parse_xml(json_txt, 'instructor'))
        loc.append(parse_xml(json_txt, 'location'))
        ty.append(parse_xml(json_txt, 'type'))
        stat.append(json_txt['availability'])
        crn.append(json_txt['crn'])
    d = {"Section": sct, "Day": day, "Time": tme, "Instructor": ins, \
            "Location": loc, "Type": ty, "Status": stat, "CRN": crn}
    df_info = pd.DataFrame(data=d)
    return df_info

# Extract div element text
def parse_xml(jt, key_str):
    
    html_txt  = html.fromstring(jt[key_str])
    value = html_txt.xpath('//div/text()')
    
    if value:
        return value[0]
    else: 
        return 'N/A'

def check_availability(status):
    """
        Input: status(Str)
        Return: Bool
        Check if status is open (includes restricted open and crosslist open)
    """
    if "open" in str.lower(status):
        return True
    else:
        return False
    
def get_soup(url):
    """
        Input: url
        Return: BeacutifulSoup instance
        Return a BeacutifulSoup instance that corresponds to the url
    """
    page = requests.get(url)

    html = page.content
    soup = BeautifulSoup(html, 'lxml')
    return soup

def get_available_course(df):
    return df[[check_availability(stat) for stat in df['Status']]]

def main():
    # input checking and utility
    # Collect query info from user
    parser = argparse.ArgumentParser(description='Find and notify if a desired course has spots.')
    parser.add_argument('-y', '--year',
                        nargs=1, default='DEFAULT',
                        help='queried year')
    parser.add_argument('-s', '--semester', 
                        nargs=1, default='DEFAULT',
                        help='queried semester')
    parser.add_argument('c', 
                        nargs='+',
                        help='queried subject. Input in the format "SubjectCode CourseNumber"')
    parser.add_argument('-crn', 
                        nargs='*',
                        help='queried CRN')
    parser.add_argument('-o', '--output',
                        nargs=1, default='./',
                        help='Specify the directory for the output file location. Default value is the current directory.')
    args = parser.parse_args()
    
    # format course to be a list of list with two entries
    # the first entry is course subject code, the second entry is course number
    queried_course = np.array(list(map(str.upper,args.c))).reshape((-1,2))
    
    # validate input year and semester and normalize
    if isinstance(args.year, list): 
        year = args.year[0]
    else:
        year = args.year
    # check year argument
    if year != "DEFAULT":
        try:
            if int(year) < 2004 or int(year) > 2018:
                print(year+": Not a valid year.")
                exit()
        except ValueError:
            print(year+": Not a valid year.")
            exit()
    # check semester argument
    if isinstance(args.semester, list): 
        semester = args.semester[0]
    else:
        semester = args.semester
    if semester != "DEFAULT":
        semester = str.lower(semester)
        if semester == 'fa' or semester == 'fall':
            semester = 'fall'
        elif semester == 'sp' or semester == 'spring':
            semester = 'spring'
        elif semester == 'su' or semester == 'sum' \
                            or semester == 'summer':
            semester = 'summer'
        elif semester == 'wi' or semester == 'winter':
            semester = 'winter'
        else:
            print(semester+": Not a valid semester.")
            exit()

    # check if the output path is valid
    if isinstance(args.output, list): 
        output = args.output[0]
    else:
        output = args.output
    if not os.path.isdir(output):
        print(output + " is not a valid directory.")
        exit()
        
    # generate url for the semester 
    url = '{}/schedule/{}/{}/'.format(base_url, year, semester)
    semester_soup = get_soup(url)

    # find the table containing both subject code and subject
    df_query_subj = semsoup2subj(semester_soup, queried_course)

    # initialize all available section queried
    available_sct = pd.DataFrame()
    # get unique subjects to extract pages from
    unique_subject = df_query_subj.code.unique()

    while True:
        for subj in unique_subject:
            # construct BeautifulSoup for page for the subject
            subject_url = url+subj
            subject_soup = get_soup(subject_url)
            # find the course queried
            course_list_xml = subject_soup.find("table", id="default-dt").find("tbody")
            
            temp_code = []
            temp_courseNum = []
            # get course number 
            for r in course_list_xml.find_all("tr"):
                # get course number
                course_xml = r.find("td")
                temp_code.append(course_xml.get_text().split()[0])
                temp_courseNum.append(course_xml.get_text().split()[1])
            # build a dataframe with subject information
            d = {"code": temp_code, "course_number": temp_courseNum} 
            df_course = pd.DataFrame(data=d)
            # find related href that corresponds to the queried courses
            df_query_course = df_course.merge(df_query_subj, \
                            left_on=['code', 'course_number'], \
                            right_on=['code', 'query_number']) \
                            .drop_duplicates() 
            # Drop replicated col: query_subject
            df_query_course.drop('query_number', axis=1, inplace=True)

            course_number = df_query_course['course_number']
            for c_num in course_number:
                # construct BeautifulSoup for page for the course
                course_url = '{}/{}'.format(subject_url,c_num)
                course_soup = get_soup(course_url)
                # construct a Dataframe for course information
                course_info = courseSoup2Df(course_soup)
                # add columns "Subject" and "Course Number" to course_info 
                course_info['Subject'] = subj
                course_info['Course Number'] = c_num
                if args.crn:
                    # find crn in current subject
                    df_in_query = course_info[course_info['CRN'].isin(args.crn)]
                    if df_in_query.empty:
                        # find open section
                        open_sct = get_available_course(course_info)
                    else:
                        open_sct = get_available_course(df_in_query)
                else:
                    # find open section
                    open_sct = get_available_course(course_info)
                available_sct = available_sct.append(open_sct, ignore_index=True)

        if not available_sct.empty:
            # reorder output dataframe
            available_sct = available_sct[['Subject', 'Course Number', \
                            'Status', 'CRN', 'Type', 'Section', 'Type',\
                            'Day', 'Location']]
            # output found open section into a file
            output_file = os.path.join(os.path.abspath(output), \
                    "available_section_from_course-availability-with-bs4.txt")
            # print available result to file
            with open(output_file, 'a') as f:
                localtime = time.asctime( time.localtime(time.time()) )
                f.write("Current Time : {}\n".format(localtime))
                f.write("Courser Availability:\nYear: {}\nSemester: {}\n".\
                        format(year, semester))
                available_sct.to_string(f)
                f.write("\n\n")
            # Trigger Notification in Mac and open file
            if "Darwin" == platform.system():
                subprocess.run('osascript -e \'display dialog "Your watched course is now available! Open Application TextEdit to see log file" with title "Course Availability" buttons {"OK"} default button "OK"\'', shell=True)
                subprocess.run('osascript -e \'tell application "TextEdit" to open POSIX file \"{}\" \''.format(output_file), \
                        shell=True)
            exit()
        else:
            # sleep for 1000 seconds and then check availability again
            time.sleep(1000)

if __name__ == '__main__':
    main()

