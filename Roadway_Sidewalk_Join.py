#-------------------------------------------------------------------------------
# Name:        Sidewalk schedule flat table geoprocessing onto roadway centerlines
# Purpose:     This script takes the road names from the roadway network centerlines file and queries the
# sidewalk schedule flat table, when road names successfully match it attempts to split the comments which are in the form "Street A to Street B"
# then geoprocesses them to select and update the correct roadway centerlines.
#
# Author:      gavinl
#
# Created:     06/03/2019
# Copyright:   (c) gavinl 2019
# Licence:     <your licence>
#-------------------------------------------------------------------------------

import arcpy
import csv

arcpy.env.overwriteOutput = True
arcpy.env.workspace = r''
arcpy.MakeFeatureLayer_management("Network_streets_Dissolved", "DissolvedRDs")
arcpy.MakeFeatureLayer_management("Sidewalk_Schedule_Edit", "Roadway_Schedule")
testing_loc = r''
Roadway_Schedule = "Roadway_Schedule"
DissolvedRDs = "DissolvedRDs"
sidewalk_tab = "Sidewalk_comments"
matchRoadCheck1 = ""
matchRoadCheck2 = ""
nonreadcount = 0
OIDMatch = ""
readcount = 0
breakcount = 0
RW_updatecount = 0
RWS_index = 0

#Records that couldn't be updated but the road exists both in the roads feature class and the schedule flat table
csvLoc = r''
#Street names that are in the centerlines feature class but have no schedule records in the flat table
csv_noSchedule = r''

#SQL arguments, hard coded to ignore invalid records that are null or cant contain sidewalks. Also ignores records that were successfully joined because the sidewalk schedule applied to an entire road
#without comments
#stcheck is based on previous script that checked if record exists in both tables

RWS_sel_SQL = "FULLNAME <> ' ' And FULLNAME <> 'S US HIGHWAY 101' And FULLNAME <> 'S FREEWAY OFF RAMP' And FULLNAME <> 'S FREEWAY ON RAMP' And schedulejoin IS NULL And stcheck = 'Yes' And 'updatecur' IS NULL"
#Sidewalk Schedule feature class fields that will ultimately be updated
updatecursor_fields = ['RW_Width','SWSchedule','SWRemark','OID@','SidewalkTabSt','updatecur','FULLNAME',"SWTabOID"]
#Fields in flat table
sch_fields =   ['OID@','FULLNAME','RW_Width']
#Used to have the script run only on records that were not successfully iterated through previously
RWS_Sel_SBA_SQL = "schedulejoin IS NULL"

def hasnumbers (inputstr):
    return any(char.isdigit() for char in inputstr)

###Create CSVs to contain failure results
##
##with open(csvLoc, mode = 'wb') as csv_file:
##    fieldnames = ['TabOID', 'stname', 'RW_Width','sidewalk_schedule', 'comments']
##    writer = csv.writer(csv_file, delimiter = ',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
##    writer.writerow(fieldnames)
##
##with open(csv_noSchedule, mode = 'wb') as csv_file:
##    fieldnames = ['TabOID', 'stname', 'RW_Width','sidewalk_schedule', 'comments']
##    writer = csv.writer(csv_file, delimiter = ',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
##    writer.writerow(fieldnames)

###For manual tested on specific reccords
#RWS_SWS_OID = 1173
#RWS_sel_SQL = "OBJECTID = {0}".format(RWS_SWS_OID)
#RWS_SWS_STName = "CROSS AVE"
#RWS_sel_SQL = "FULLNAME = '{0}'".format(RWS_SWS_STName)


#Count how many records will be iterated through in roadway schedule feat class
sch_cursor_index =  arcpy.da.SearchCursor(Roadway_Schedule, sch_fields, RWS_sel_SQL)
for sch_row_index in sch_cursor_index:
    RWS_index += 1

print ("Total street names to be checked: {0}".format(RWS_index))
#Iterate through roadway centerlines road names and feed into nested cursor searching through sidewalk schedule flat table for name matches
#

sch_cursor =  arcpy.da.SearchCursor(Roadway_Schedule, sch_fields, RWS_sel_SQL)
for sch_row in sch_cursor:


    #print ("  ")
    print("Roadway sidewalk schedule street name is: {0}".format(sch_row[1]))
    #print ("Roadway Schedule OID is: {0}".format(sch_row[0]))
    #print("Roadway sidewalk schedule roadway width is: {}".format(sch_row[2]))
    RWS_index -= 1
    print ("There are {0} remaining street names to geoprocess".format(RWS_index))
    reviewST = str(sch_row[1])
    sidewalktab_clause = "ST = '{0}'".format(reviewST)
    #print ("Sidewalk clause is: {0}".format(sidewalktab_clause))
    sidewalktab_fields = ['OBJECTID', 'ST', 'R_W__WIDTH', 'SIDEWALK__SCHEDULE', 'REMARKS']


    #Used to check if cursor is empty (failed to query any records), if empty put street details into csv
    row  = None

    #Iterate through sidewalk schedule flat table looking for street names coming from roadway feat class road names
    #If no match, row is None, means that the street name exists in roadway network but not in the schedule flat table
    cursor = arcpy.da.SearchCursor(sidewalk_tab, sidewalktab_fields, sidewalktab_clause)
    for row in cursor:

        TabOID = str(row[0])
        stname = str(row[1])
        print("Sidewalk flat table st name is : {0}".format(stname))
        RW_Width = str(row[2])
        print("Roadway Schedule flat table Width is: {0}".format(RW_Width))
        sidewalk_Schedule = str(row[3])
        comments = str(row[4])
        print ("Comment is: {0}".format(comments))

        #Check to see if comments follow "Road A to Road B" format, if not write details to csv for manual review
        if " TO " in comments:
            matchRoadCheck1 = comments.split(" TO ",1)[0]
            matchRoadCheck2 = comments.split(" TO ",1)[1]
            #Check to see if there are any numbers, if so write details to csv for manual review
            if (hasnumbers(matchRoadCheck1) == False and hasnumbers(matchRoadCheck2) == False):
    ##                print ("Has two matching road names")
    ##                print ("Sidewalk table OID is: " + TabOID)
    ##                print ("Sidewalk street name is: " + stname)
    ##                print ("Crossroad 1 selection is: " + matchRoadCheck1)
    ##                print ("Crossroad 2 selection is: " + matchRoadCheck2)


                whereclause1 = "FULLNAME IN ('{0}','{1}','{2}')".format(stname,matchRoadCheck1,matchRoadCheck2)
                whereclause2 = "FULLNAME = '{0}'".format(stname)
                whereclause3 = "FULLNAME = '{0}'".format(matchRoadCheck1)
                whereclause4 = "FULLNAME = '{0}'".format(matchRoadCheck2)

                #Select from dissolved roads the three roads of interest. Dissolved roads are needed since centerlines are segmented at each intersection and
                #schedule information may pass through many intersections
                DisRD_SBA = arcpy.SelectLayerByAttribute_management(DissolvedRDs, "NEW_SELECTION", whereclause1)
                DisRD_SBA_GT = str(arcpy.GetCount_management(DisRD_SBA))
                #print("There are {0} selected dissolved roadway centerlines when selecting street name and to-from streets, should be 2 or 3".format(DisRD_SBA_GT))
                arcpy.MakeFeatureLayer_management(DisRD_SBA,"DisRDSel")

                #Take selected dissolved lines and apply featre to line, this will resegment the lines at their intersections with each other. Needed to allow
                #the later selection of only the lines between the two cross streets
                arcpy.FeatureToLine_management("DisRDSel","in_memory/featToLine")
                arcpy.MakeFeatureLayer_management("in_memory/featToLine","featToLineLyr")
                #testing
                #arcpy.CopyFeatures_management("featToLineLyr",r'\\vgisdata\GIS Data\GIS_Projects\GavinLeavitt\sidewalk_schedule\testing.gdb\featToLineLyr')

                ###Turn feature to line results into feature layers for each street
                FeatToLine_SBA_PS = arcpy.SelectLayerByAttribute_management("featToLineLyr", "NEW_SELECTION", whereclause2)
                FeatToLine_SBA_PS_GT = str(arcpy.GetCount_management(FeatToLine_SBA_PS))
                #print("There are {0} selected records in Feature to Line results using sidewalk section street name, should be > 0".format(FeatToLine_SBA_PS_GT))
                arcpy.MakeFeatureLayer_management(FeatToLine_SBA_PS, "PrimaryST")
                #testing
                #arcpy.CopyFeatures_management("PrimaryST",r'\\vgisdata\GIS Data\GIS_Projects\GavinLeavitt\sidewalk_schedule\testing.gdb\PrimaryST')

                ###Turn feature to line results into feature layers for each street
                FeatToLine_SBA_SS = arcpy.SelectLayerByAttribute_management("featToLineLyr", "NEW_SELECTION", whereclause3)
                FeatToLine_SBA_SS_GT = str(arcpy.GetCount_management(FeatToLine_SBA_SS))
                #print("There are {0} selected records in the secondary street selection, should be > 0".format(FeatToLine_SBA_SS_GT))
                arcpy.MakeFeatureLayer_management(FeatToLine_SBA_SS, "SecondaryST")
                #testing
                #arcpy.CopyFeatures_management("SecondaryST",r'\\vgisdata\GIS Data\GIS_Projects\GavinLeavitt\sidewalk_schedule\testing.gdb\SecondaryST')

                ###Turn feature to line results into feature layers for each street
                FeatToLine_SBA_TS = arcpy.SelectLayerByAttribute_management("featToLineLyr", "NEW_SELECTION", whereclause4)
                FeatToLine_SBA_TS_GT = str(arcpy.GetCount_management(FeatToLine_SBA_TS))
                #print("There are {0} selected records in the tertiary street selection, should be > 0".format(FeatToLine_SBA_TS_GT))
                arcpy.MakeFeatureLayer_management(FeatToLine_SBA_TS, "TertiaryST")
                #testing
                #arcpy.CopyFeatures_management("TertiaryST",r'\\vgisdata\GIS Data\GIS_Projects\GavinLeavitt\sidewalk_schedule\testing.gdb\TertiaryST')


                ###Select the primary street centerlines (street to be updated with sidewalk schedule) where they intersect the secondary street cross street. (This is "Street A" in the "Street A to Street B" comment)
                ###10 foot range is used since some streets are not properly snapped together. This will select both sides of the primary road, oneside is not between A and B
                FeatToLine_SBL_SS = arcpy.SelectLayerByLocation_management("PrimaryST", 'INTERSECT', "SecondaryST", "10 feet", "NEW_SELECTION")
                FeatToLine_SBL_SS_GT = str(arcpy.GetCount_management(FeatToLine_SBL_SS))
                #print("There are {0} selected records in the primary-secondary Select By Location selection, should be > 0".format(FeatToLine_SBL_SS_GT))
                arcpy.MakeFeatureLayer_management(FeatToLine_SBL_SS, "FeatToLine_SBL_SS_LYR")
                #testing
                #arcpy.CopyFeatures_management("FeatToLine_SBL_SS_LYR",r'\\vgisdata\GIS Data\GIS_Projects\GavinLeavitt\sidewalk_schedule\testing.gdb\FeatToLine_SBL_SS_LYR')

                ###Do a new selection based on the previous selection using Street B, this will return the dissolved primary road between A and B
                FeatToLine_SBL_ST = arcpy.SelectLayerByLocation_management("FeatToLine_SBL_SS_LYR", 'INTERSECT', "TertiaryST", "10 feet", "NEW_SELECTION")
                FeatToLine_SBL_ST_GT = str(arcpy.GetCount_management(FeatToLine_SBL_ST))
                #print("There are {0} selected records in the secondary-tertiary Select By Location selection, should be > 0".format(FeatToLine_SBL_ST_GT))
                arcpy.MakeFeatureLayer_management(FeatToLine_SBL_ST, "DisRD_SW_Lines")
                #testing
                #arcpy.CopyFeatures_management("DisRD_SW_Lines",r'\\vgisdata\GIS Data\GIS_Projects\GavinLeavitt\sidewalk_schedule\testing.gdb\DisRD_SW_Lines')

                #Use the previous dissolved roadway selection to select the original roadway centerline lines that lie under the dissolved roadways (These roadway segments were used to generate
                #the dissolved roadway feat class)
                #Final selection
                RWS_Sel = arcpy.SelectLayerByLocation_management(Roadway_Schedule, 'WITHIN', "DisRD_SW_Lines", "0", "NEW_SELECTION")
                RWS_Sel_GT = str(arcpy.GetCount_management(RWS_Sel))
                print("There are {0} selected records in the roadway SBL to be updated".format(RWS_Sel_GT))

                #Select the roadway centerlines that have not been previously updated using an update cursor
                #This section of code probably not needed anymore
                RWS_Sel_SBA = arcpy.SelectLayerByAttribute_management(RWS_Sel,"SUBSET_SELECTION",RWS_Sel_SBA_SQL)
                RWS_Sel_SBA_GT = str(arcpy.GetCount_management(RWS_Sel_SBA))
                print("There are {0} selected records in the final roadway SBA to be updated".format(RWS_Sel_SBA_GT))


                print("Selections Complete, attaching tabular Schedule records to Roadway Schedule")
                if RWS_Sel_SBA_GT == "0":
                    #No final selection occurred but street names appear valid
                    print("No final selection results")
##                    with arcpy.da.SearchCursor(RWS_Sel, ["Network_streets_Edit_RW_Width","Network_streets_Edit_SWSchedule","Network_streets_Edit_SWRemark","OID@","Network_streets_Edit_SidewalkTabSt","updatecur"], RWS_sel_SQL) as nullsearchcursor:
##                        for nullsearchrow in nullsearchcursor:
##                            nonreadcount += 1
##                            with open(csvLoc, mode = 'ab') as csv_file:
##                                writer = csv.writer(csv_file, delimiter = ',')
##                                writer.writerow([TabOID,stname,RW_Width,sidewalk_Schedule,comments])

    ##            for rowprime in arcpy.da.SearchCursor(Roadway_Schedule, ["OID@"]):
    ##                OID = int(rowprime[0])
    ##                print ("Join OID is: {0}".format(TabOID))


                #Update roadway centerlines with sidewalk schedule information
                else:
                    with arcpy.da.UpdateCursor(RWS_Sel_SBA, updatecursor_fields) as updatecursor:
                        for updaterow in updatecursor:
                            print("Update Cursor Active")
                            print("Original update row value is {0}".format(updaterow[0]))
                            updaterow[0] = RW_Width
                            print ("##############Update RW_Width is: {0}".format(updaterow[0]))
                            updaterow[1] = sidewalk_Schedule
                            print ("Update sidewalk_schedule is: {0}".format(updaterow[1]))
                            updaterow[2] = str(comments)
                            updaterow[4] = stname
                            updaterow[5] = "Within method - 20190425"
                            updaterow[7] = TabOID
                            print("Update street name is: {0}".format(stname))
                            RW_updatecount += 1
                            updatecursor.updateRow(updaterow)

                            #print ("### Update cursor values are: ###")
        ##                  RWS_sel_cursor = arcpy.da.SearchCursor(RWS_sel, "OID@")
        ##                  for OIDrow in RWS_sel_cursor:
        ##                  print ("Roadway Centerline OID to be updated is: {0}".format(OIDrow[0]))
                            #print ("Roadway Centerline OID is :{0}".format(updaterow[4]))
                            #print ("TabOID is : {0}".format(updaterow[0]))
                            #print ("Using update cursor on {0}".format(updaterow[3]))
                            #print ("Update describtion is: {0}".format(updaterow[3]))
                            #print ("End Update Variables")

                            #print ("Breakcount is: {0}".format(breakcount))

                            #print ("Finished updating Roadway sidewalk schedule with Sidewalk Schedule flat table OID: {0}".format(TabOID))
                            #print ("Roadway sidewalk schedule update count is: {0}".format(RW_updatecount))
                #exit()

            else:
               #These sidewalk comments containing numbers, such as "123 Main st to Lincoln Ave" and cannot be resolved by this script, right to file for manual review
               print("Road names have numbers, can't match")
               nonreadcount += 1
##                #print ("Non-readable")
##                #print ("OID is: " + TabOID)
##                #print ("Crossroad 1 selection is: " + matchRoadCheck1)
##                #print ("Crossroad 2 selection is: " + matchRoadCheck2)
##                with open(csvLoc, mode = 'ab') as csv_file:
##                    writer = csv.writer(csv_file, delimiter = ',')
##                    writer.writerow([TabOID,stname,RW_Width,sidewalk_Schedule,comments])
##                #print ("Can't update")

##                #print (" ")
        ##        with open(csvLoc, mode = 'ab') as csv_file:
        ##            writer = csv.writer(csv_file, delimiter = ',')
        ##            writer.writerow([TabOID,stname,RW_Width,sidewalk_Schedule,comments])

        else:
            #There is no "TO" in comment section but there is some kind of comment description
            print ("No ""TO"" in comments")
            nonreadcount += 1
            #print (" ")
    if not row:
        print ("No table match, value is in roadway table but not in sidewalk schedule flat table")
        nonreadcount += 1
        with open(csv_noSchedule, mode = 'ab') as csv_file:
            writer = csv.writer(csv_file, delimiter = ',')
            writer.writerow([sch_row[0],sch_row[1]])


print ("#########################################################################")
#print ("Sidewalk Schedule CSV Non-readable count is: {0}".format(nonreadcount))
#print ("Sidewalk Schedule CSV Readable count is: {0}".format(readcount))
print ("Roadway update count is: {0}".format(RW_updatecount))
del(Roadway_Schedule)
del(sidewalk_tab)
##del(updatecursor)
##del(updaterow)
print ("All Done!")