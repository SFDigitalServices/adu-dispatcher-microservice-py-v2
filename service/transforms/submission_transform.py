""" Submission Transform module """
#pylint: disable=too-few-public-methods
import os
import json
from .transform import TransformBase

class SubmissionTransform(TransformBase):
    """ Transform for Export Submissions """
    def transform(self, data):
        """
        transform submissions
        """
        # get record template
        with open('service/templates/accela_submission.json', 'r') as file_obj:
            template_record = json.load(file_obj)
        output = self.populate_template(template_record, data)
        return output

    @staticmethod
    #pylint: disable=too-many-locals
    def populate_template(template, submission):
        """ Populate template with submission data """
        record = template
        data = submission['data']
        record['name'] = data['projectAddress']
        parcel = data['projectAddressBlock'] + data['projectAddressLot']
        record['parcels'][0]['parcelNumber'] = parcel

        # address
        address = {
            "streetName": data['projectAddressStreetName'],
            "streetStart": data['projectAddressNumber'],
            "postalCode": data['projectAddressZip'],
            "streetSuffix": {
                "text": data['projectAddressStreetType'],
                "value": data['projectAddressStreetType']
            },
            "unitStart": data['projectAddressUnitNumber'],
            "neighborhood": parcel
        }
        record['addresses'].append(address)

        # PLN_PRJ-ENTITLEMENT.cTYPE
        record['customForms'].append({
            "id": "PLN_PRJ-ENTITLEMENT.cTYPE",
            "Job Value": data['estimatedConstructionCost']
        })

        # PLN_PRJ-PROJECT.cDESCRIPTION
        if 'whereProposedAduLocated' in data:
            proj_desc = {
                "id": "PLN_PRJ-PROJECT.cDESCRIPTION",
                "Additions": "",
                "New Construction": ""
            }
            if data['whereProposedAduLocated'] == 'newConstruction':
                proj_desc['New Construction'] = 'CHECKED'
            if data['whereProposedAduLocated'] == 'addition':
                proj_desc['Additions'] = 'CHECKED'
            record['customForms'].append(proj_desc)

        # PLN_PRJ-RESIDENTIAL.cTYPE
        residential_type = {
            "id": "PLN_PRJ-RESIDENTIAL.cTYPE",
            "Change of Dwelling Units": "No",
            "Accessory Dwelling Unit": "CHECKED"
        }
        if data['existingDwellingUnits'] != data['newDwellingUnits']:
            residential_type['Change of Dwelling Units'] = 'Yes'
        record['customForms'].append(residential_type)

        # PLN_PRJ-PROJECT.cFEATURES
        proj_feature = {
            "id": "PLN_PRJ-PROJECT.cFEATURES",
            "rows": [
                {
                    "action": "add",
                    "fields": {
                        "Project Feature": "Dwelling Units-Market Rate",
                        "Proposed Unit(s)": data['newDwellingUnits'],
                        "Existing Unit(s)": data['existingDwellingUnits']
                    }
                }
            ]
        }
        record['customTables'].append(proj_feature)

        # PLN_PRJ-LAND.cUSE.c.1.cRESIDENTIAL
        proj_residential = {
            "id": "PLN_PRJ-LAND.cUSE.c.1.cRESIDENTIAL",
            "rows": []
        }
        for row in data['proposedAdUs']:
            adu_type_map = {
                "Studio": "ADU Studio",
                "1Bedroom": "ADU One Bedroom",
                "2Bedroom": "ADU Two Bedroom",
                "3Bedroom": "ADU Three Bedroom (and +)"
            }
            adu = {
                "action" : "add",
                "fields": {
                    "Dwelling Unit Type": adu_type_map[row['proposedUnitType']],
                    "Proposed": "1",
                    "Existing": "0",
                    "Net": "1",
                    "ADU Area": row['proposedSquareFootage']
                }
            }
            proj_residential['rows'].append(adu)

        record['customTables'].append(proj_residential)

        # contacts
        contact_applicant = {
            "firstName": data['firstName'],
            "lastName": data['lastName'],
            "email": data['email'],
            "phone1": data['phoneNumber'],
            "type": {
                "text": "Applicant",
                "value": "Applicant"
            }
        }
        record['contacts'].append(contact_applicant)

        contact_billing = {
            "firstName": data['firstName'],
            "lastName": data['lastName'],
            "email": data['email'],
            "phone1": data['phoneNumber'],
            "type": {
                "text": "Billing Contact",
                "value": "Billing Contact"
            }
        }

        if data['billingFirstName'] and data['billingLastName']:
            contact_billing['firstName'] = data['billingFirstName']
            contact_billing['lastName'] = data['billingLastName']
            contact_billing['email'] = data['billingEmail']
            contact_billing['phone1'] = data['billingPhoneNumber']

        record['contacts'].append(contact_billing)

        # comments uploads
        comment_upload = ""

        upload_map = {
            "uploadPRJ" : "PRJ application",
            "uploadADUChecklist" : "ADU checklist",
            "uploadADUScreening" : "ADU screening form",
            "uploadFixtureCount" : "Fixture Count form",
            "uploadStreetTree" : "Street tree application and guidelines",
            "uploadTreePlantingChecklist" : "Tree planting and protection checklist"
        }
        for upload_field in upload_map:
            if upload_field in data:
                upload_line = upload_map[upload_field] + ': '
                upload_line += os.environ.get('UPLOAD_HOST') + '/' + data[upload_field][0]['key']
                comment_upload += upload_line + ' \n\n'

        comment_upload += 'Plans : \n'
        for plan in data['uploadPlans']:
            upload_line = '* ' + os.environ.get('UPLOAD_HOST') + '/' + plan['key']
            comment_upload += upload_line + ' \n\n'

        record['comments'].append({"text": comment_upload})

        return record
