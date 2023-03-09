# -*- coding: utf-8 -*-

import argparse
import pandas as pd
import xnat
import sys
import os
import getpass
import tempfile
#
from . __version__ import __version__
from downloadtools.utils import dbreader
#from downloadtools import dbsearch
from downloadtools.utils import download_dcm
from downloadtools.utils import checkdatabase
from downloadtools.utils import anonymize
from downloadtools.utils import convert2nii
from downloadtools.utils import download_dcm_noid
from downloadtools.utils import download_dcmname
#from downloadtools.utils import move_to_dest
from downloadtools.utils import makebids
from downloadtools.utils import checkdatabasesubject
#%%
def main():
    
       
    if hasattr(sys, "ps1"):
        project = "01-M-0192"
        dosnapshot = False
        sdanid = ["24573","24475", "24522","24509","24518"]
        #sdanid = False
        date = [""]#["2023","02-07-2023"]
        download = True
        SeriesName = [""]
        unzip = True
        keepdicom = False
        search_name = False
        downloaddir = "/EDB/SDAN/temp/test02-14-2"
        user = None
        password = None
        MRNid = None 
        dosnapshotsubject = False
        search_robin = True
        dobids = True
        
        #os.environ["TMP"] = "/EDB/SDAN/temp/"
    else :
        parser = argparse.ArgumentParser(description="Download data from XNAT v {}. Created by Andre Zugman".format(__version__))
        parser.add_argument('-v', '--version', action='version',
                    version='version: {}'.format(__version__))
        parser.add_argument('-i', '--id', nargs='+',dest="id", action='store', type=str, required=False,
                            help='id of subject or list of subjects')
        parser.set_defaults(id=None)
        parser.add_argument('-o','--output', action='store', type=str, required=True,
                            help='output path.')
        parser.add_argument('-d', '--date', nargs='+',action='store', dest="date", type=str, required=False,
                            help='Session Date in mm-dd-yyyy (i.e.: 12-30-2022).')        
        parser.set_defaults(date=[""])
        parser.add_argument('--dosnapshot', action='store_true',dest='dosnapshot',
                            help='save a table with info of data stored in the project.')
        parser.set_defaults(dosnapshot=False)
        parser.add_argument('-s', '--series', nargs='+', action='store', dest='SeriesName', type=str,
                            help='Series Name')
        parser.add_argument('-p', '--project', action='store', dest='project', type=str,
                            help='project name - as defined in xnat')
        parser.add_argument('--keepdicom', action='store_true',dest='keepdicom',
                            help='Keep the dicoms. This will not run dcm2niix and keep anonymized dicoms.')
        parser.set_defaults(keepdicom = False)
        parser.add_argument('--search_name', action='store_true',dest='search_name',
                            help='Search XNAT by name and not MRN. Default is to search by MRN, and if MRN not found search for Name')
        parser.set_defaults(search_name = False)
        parser.add_argument('--dobids', action='store_true',dest='dobids',
                            help='Export a BIDS directory.')
        parser.set_defaults(dobids = False)
        parser.add_argument('--not-robin', nargs='+', type=str, action='store',dest='MRNid',
                            help="""Do not use robin id. In this case provide the MRN manually with no "-".
                            You can also use this with other ID (i.e.: NDAR GUID). In this case the data will use the id provided.
                            Only use this if you are sure it is safe to do so.""")
        parser.set_defaults(MRNid = None)
        parser.set_defaults(SeriesName=[""])
        parser.set_defaults(project="01-M-0192")
        args = parser.parse_args()
        #print(parser.print_help())
        project = args.project
        dosnapshot = args.dosnapshot
        sdanid = args.id
        date = args.date
        download = True
        SeriesName = args.SeriesName
        keepdicom = args.keepdicom
        search_name = args.search_name
        unzip = True
        downloaddir = args.output
        user = None
        password = None
        dosnapshotsubject = False
        dobids = args.dobids
        MRNid = args.MRNid
    #just setting some options
    if dosnapshot and  isinstance(sdanid, list):
        dosnapshotsubject = True
        download = False
        dosnapshot = False
    if keepdicom :
        dobids = False
    if MRNid is None :
        search_robin = True
    else :
        search_robin = False
    if search_name:
        search_robin = False
    if sdanid is not None :
        sdanid = " ".join(sdanid).split(" ")
        while "" in sdanid:
            sdanid.remove("")
        while " " in sdanid:
            sdanid.remove(" ")
    else :
        sdanid = False
    if MRNid is not None:
        MRNid = " ".join(MRNid).split(" ")
        while "" in sdanid:
            MRNid.remove("")
        while " " in sdanid:
            MRNid.remove(" ")
    if all([x=="" for x in date]):
        
        if sdanid != False and len(sdanid) != len(date):
            date = [""]*len(sdanid)
    else :
        date = " ".join(date).split(" ")
        while date[-1] == "" :
            date = date[:-1]
        while date[-1] == " ":
            date = date[:-1]
        if sdanid != False and len(sdanid) != len(date):
            print("Number of dates and id is different. Will search without date for the last ids")
            diffdates = len(sdanid) - len(date)
            if diffdates >= 1:
                date = date + [""]*diffdates
            elif diffdates < 0: 
                sys.exit("You provided more dates than subjects. Double check what you are doing")
    if not os.path.exists(os.path.join("/home",os.environ["USER"],".netrc")) :
        print (".netrc file not found. Prompting for username and password")
        user = getpass.getuser()
        print ("current user is {}".format(user))
        password = getpass.getpass(prompt="Please enter Password : ")
    with xnat.connect("https://fmrif-xnat.nimh.nih.gov", user=user, password=password) as xsession :
        if not (os.getenv("TMPDIR") or os.getenv("TEMP") or os.getenv("TMP")) :
            print("WARNING : tempfile not specified by user. Please consider setting your TMP path before running this script" )
            print("Please type : export TMP=/home/{}/tmp or some other approapriate path.".format(getpass.getuser()))
            print("using system default may cause problems")
            print("Will try /home/{}/tmp".format(getpass.getuser()))
            tempfile.tempdir = "/home/{}/tmp".format(getpass.getuser())
            if not os.path.isdir("/home/{}/tmp".format(getpass.getuser())) :
                os.makedirs("/home/{}/tmp".format(getpass.getuser()))
            
        if dosnapshot :
            dbsearched = dbreader(0)
            dbsearched["subjects"] = dbsearched.loc[:,1].str.replace("-","")
            dbsearched["subjects"] = dbsearched.loc[:,"subjects"].str.replace(r"[a-z]+","", regex=True)
            dbsearched["subjects"] = dbsearched.loc[:,"subjects"].str.replace(r"[A-Z]+","", regex=True)
            dbsearched["subjects"] = dbsearched.loc[:,"subjects"].str.replace(",","")
            dbsearched["subjects"] = pd.to_numeric(dbsearched["subjects"], errors = "coerce", downcast="integer")
            dbsnapshot = checkdatabase(xsession, project)
            dbsnapshot.to_csv(os.path.join(downloaddir,"dbsnapshot-xnatpartial.csv"),index = False)
            dbsnapshot["subjects"] = pd.to_numeric(dbsnapshot["subjects"],errors = "coerce", downcast="integer")
            dbsnapshot = dbsnapshot.merge(dbsearched,on= "subjects",how="inner")
            dbsnapshot = dbsnapshot.rename(columns={0: "sdanid", 1: "MRN", 2: "DOB",3: "Last Name", 4: "First Name" })
            dbsnapshot.drop([5,6,7], axis = 1, inplace = True)
            #dbsnapshot["subjects"] = dbsnapshot["subjects"].astype(int)
            dbsnapshot = dbsnapshot.reindex(columns= ['sdanid', 'MRN',"AccessionNumber",
                   'DOB', 'Last Name', 'First Name','seriesName', 'uri', 'date-series', 'date-session'])
            os.makedirs(os.path.join(downloaddir),  exist_ok = True) 
            dbsnapshot.to_csv(os.path.join(downloaddir,"dbsnapshot.csv"),index = False)
    
            download = False
        
        if dosnapshotsubject :
            for idd,i in enumerate(sdanid) :
                try :
                    dbsnapshot = checkdatabasesubject(xsession, project, i, MRNid[idd])
                    if os.path.isfile(os.path.join(downloaddir,"dbsnapshot.csv")):
                        dbsnapshot.to_csv(os.path.join(downloaddir,"dbsnapshot.csv"),index = False, header=False,mode="a")
                    else:
                        dbsnapshot.to_csv(os.path.join(downloaddir,"dbsnapshot.csv"),index = False) 
                except KeyError:
                    print("subject:{} not in this XNAT project".format(i))
        if download :
            #set up temp folder to work on
            #tempfile.tempdir=tempfile.gettempdir()
            os.makedirs(os.path.join(downloaddir),  exist_ok = True)
            with tempfile.TemporaryDirectory(suffix=None, prefix=None) as tempdir :
            
                if sdanid :
                    for idd,i in enumerate(sdanid) :
                        
                        #print (i)
                        if search_robin :
                            dbsearched = dbreader(i)
                            MRN = dbsearched.loc[0,1]
                            MRN = MRN.replace("-","")
                            LastName = dbsearched.loc[0,3]
                            LastName = LastName.replace(",","")
                            FirstName = dbsearched.loc[0,4]
                        else :
                            MRN = MRNid[idd]
                        try: 
                            download_dcm(xsession, project, MRN, i, date[idd], SeriesName, tempdir, unzip )
                            if keepdicom :
                                downloaddirlocal = os.path.join(downloaddir,"dicom")
                                anonymize(tempdir,downloaddirlocal, i)
                            else :
                                downloaddirlocal = os.path.join(downloaddir,"nifti")
                                convert2nii(tempdir,downloaddirlocal, i)
                        except :
                        #    search_name = True
                            print("Error downloading using MRN.")
                            print("subject:{} Check if this subject is in XNAT project {}".format(i, project))
                        if search_name :
                            print ("Downloading by Name")
                            
                            download_dcmname(xsession, project, FirstName, LastName, i, date[idd], SeriesName, tempdir, unzip)
                            if keepdicom :
                                downloaddirlocal = os.path.join(downloaddir,"dicom")
                                anonymize(tempdir,downloaddirlocal, i)
                            else :
                                downloaddirlocal = os.path.join(downloaddir,"nifti")
                                convert2nii(tempdir,downloaddirlocal, i)
                if not sdanid :
                    print ("no id provided - looking for date")
                    print ("this can take longer. Please wait")
                    if not search_robin :
                        print ("you cannot look by date without robin. Data would keep MRN")
                        sys.exit("ERROR")
                    sdanid = download_dcm_noid( xsession, project, date, SeriesName, tempdir, unzip)
                    for i in sdanid :
                        if keepdicom :
                            downloaddirlocal = os.path.join(downloaddir,"dicom")
                            anonymize(tempdir,downloaddirlocal, i)
                        else :
                            downloaddirlocal = os.path.join(downloaddir,"nifti")
                            convert2nii(tempdir,downloaddirlocal, i)
                
                if dobids :
                    makebids(downloaddirlocal,tempdir, True)
        
          
if __name__ == '__main__':
    main()
