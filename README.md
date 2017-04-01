## Course Availability Checker 
This is a simple Course Availability Checker for UIUC courses.
This is a project inspired by INFO490 Advanced Data Science and mained implemented with BeautifulSoup.
User will need to input the subject and course number he/she wants to check availbaility, with year, semester, crn as an option, and if you're a Mac user, when a course is found, a notificatin from Mac will show up, and a log file with found available session will be open.

## Usage
```
python3 course-availability.py

usage: course-availability.py [-h] [-y YEAR] [-s SEMESTER]
                              [-crn [CRN [CRN ...]]] [-o OUTPUT]
                              c [c ...]

Find and notify if a desired course has spots.

positional arguments:
  c                     queried subject. Input in the format "SubjectCode
                        CourseNumber"

optional arguments:
  -h, --help            show this help message and exit
  -y YEAR, --year YEAR  queried year
  -s SEMESTER, --semester SEMESTER
                        queried semester
  -crn [CRN [CRN ...]]  queried CRN
  -o OUTPUT, --output OUTPUT
                        Specify the directory for the output file location.
                        Default value is the current directory.
```

### Example Inputs
```
# basic input
python3 course-availability.py CS 374 "Information Sciences" 490

# specify CRN
# For example, only interested in IS490 "Foundations of Data Science", with crn 68792
python3 course-availability.py CS 374 "Information Sciences" 490 -crn 68792

# specify Year or Semester, or both
# Fall semester can be "fa" or "fall"
# Spring semester can be "sp" or "spring"
# Summer semester can be "su" or "summer"
# Winter semester can be "wi" or "winter"
python3 course-availability.py -y 2017 -s fa IS 490
python3 course-availability.py -y 2017 -s fall IS 490
```