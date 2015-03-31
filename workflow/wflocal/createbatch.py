import csv
import os
import shutil
import sys
import drlutils.collection_building.utils
import drlutils.mods.marc2DrlMods
from workflow.wflocal.models import *
import workflow.core.models
import workflow.core.createbatch

def handle_files(this_item, file_string):
    """lower-case filenames per local practice"""
    if file_string:
        workflow.core.createbatch.handle_files(this_item, file_string)
        files = file_string.split(',')
        for file in files:
            file_name =  file.strip()
            i_f  = workflow.core.models.Item_File.objects.get(item=this_item, name=file_name)
            i_f.name = i_f.name.lower()
            i_f.save()

def validate_csv(batch, csv_file):
    """check for expected data based on local content models"""
    errors = [] 
    copyright_values = ['unknown', 'copyrighted', 'pd', 'pd_expired', 'pd_usfed', 'pd_holder', 'pd_expired']
    publication_values = ['unknown', 'published', 'unpublished']
    type = batch.type 
    collection = batch.collection 
    try:
        for line in csv_file:
            repository_path = os.path.join('/usr/local/dlxs/repository', collection.c_id[0], collection.c_id, line['id'])
            if os.path.exists(repository_path):
                errors.append('WARNING: Repository path already exists for item: ' + line['id'])
            if type.name in ['text - cataloged', 'text - uncataloged']:
    #           #check for presence of rights and publication status data    
    #            if not line['copyright_status'] in copyright_values: 
    #                errors.append('Missing or incorrect data in copyright_status field for item: ' + line['id'])
    #            if not line['publication_status'] in publication_values: 
    #                errors.append('Missing or incorrect data in publication_status field for item: ' + line['id'])
    #            # if copyright status is 'copyrighted', 'copyright_holder_name' data must be present
    #            if line['copyright_status'] == 'copyrighted' and not line['copyright_holder_name']:
    #                errors.append('Missing data in copyright_holder_name field for copyrighted item: ' + line['id'])
    #            # check that if there is 'date issued' data, there is also a value in enumeration
    #            if 'date_issued' in csv_file.fieldnames and line['date_issued'] and not line['enumeration']:
    #                errors.append('Missing data in enumeration field for item: ' + line['id'])
                if type.name == 'text - cataloged':
                    if not line['voyager_id']:
                        errors.append('Missing data in voyager_id field for item: ' + line['id'])
                    marcxml_file = '/usr/local/dlxs/prep/m/marcxml/' + line['voyager_id'] + '.marcxml.xml'
                    if not os.path.exists(marcxml_file):
                        errors.append('Missing marcxml file on disk for item: ' + line['id'])
            elif type.name == 'manuscript':
                if not line['ead_id']:
                    errors.append('Missing data in ead_id field for item: ' + line['id'])
                mods_file = '/usr/local/dlxs/prep/m/mods/' + line['id'] + '.mods.xml'
                if not os.path.exists(mods_file):
                    errors.append('Missing mods file on disk for item: ' + line['id'])
            elif type.name == 'image':
                if not line['files']:
                    errors.append('Missing data in files field for item: ' + line['id'])
        if len(errors) > 0:
            error_string = '\n'.join(errors)
            raise Exception(error_string)
        else:
            return
    except KeyError as ke:
        error_string = 'Missing expected field in CSV header: ' + str(ke)
        raise Exception(error_string)
    except Exception as e:
        error_string = 'Bad CSV data:\n' + str(e)
        raise Exception(error_string)


def validate_item(cleaned_data):
    item_dict = {}
    item_dict['type'] = cleaned_data['type'].name
    item_dict['collection_id'] = cleaned_data['collection'].c_id
    item_dict['do_id'] = cleaned_data['item_do_id']
    item_dict['copyright_status'] = cleaned_data['copyright_status']
    item_dict['publication_status'] = cleaned_data['publication_status']
    item_dict['copyright_holder_name'] = cleaned_data['copyright_holder_name']
    item_dict['enumeration'] = cleaned_data['enumeration']
    item_dict['date_issued'] = cleaned_data['date_issued']
    item_dict['voyager_id'] = cleaned_data['voyager_id']
    item_dict['ead_id'] = cleaned_data['ead_id']
    _validate(item_dict)


def _validate(item_dict):
    """
    Check for expected data based on local content models.

    @param item_dict
    should have keys:
        'type' - string represenation of item type
        'collection_id' - collection id
        'do_id' - item digital object id
        'copyright_status' - 
        'publication_status' -
        'copyright_holder_name' -
        'enumeration'
        'date_issued'
        'voyager_id'
        'ead_id'
        'item_files'

    """
    errors = [] 
    copyright_values = ['unknown', 'copyrighted', 'pd', 'pd_expired', 'pd_usfed', 'pd_holder', 'pd_expired']
    publication_values = ['unknown', 'published', 'unpublished']
    try:
        type = item_dict['type'] 
        c_id = item_dict['collection_id'] 
        do_id = item_dict['do_id']
        repository_path = os.path.join('/usr/local/dlxs/repository', c_id[0], c_id, do_id)
        if os.path.exists(repository_path):
            errors.append('WARNING: Repository path already exists for item: ' + do_id)
    
        #if type in ['text - cataloged', 'text - uncataloged']:
            #check for presence of rights and publication status data    
            #if not item_dict['copyright_status'] in copyright_values: 
            #    errors.append('Missing or incorrect data in copyright status field for item: ' + do_id)
            # if not item_dict['publication_status'] in publication_values: 
            #    errors.append('Missing or incorrect data in publication_status field for item: ' + do_id)
            # if copyright status is 'copyrighted', 'copyright_holder_name' data must be present
            #if item_dict['copyright_status'] == 'copyrighted' and not item_dict['copyright_holder_name']:
            #    errors.append('Missing data in copyright holder name field for copyrighted item: ' + do_id)
            # check that if there is 'date issued' data, there is also a value in enumeration
            #if item_dict['date_issued'] and not item_dict['enumeration']:
            #    errors.append('Missing data in enumeration field for item having year issued: ' + do_id)

        if type == 'manuscript':
            if not item_dict['ead_id']:
                errors.append('Missing data in ead_id field for item: ' + do_id)
            mods_file = '/usr/local/dlxs/prep/m/mods/' + do_id + '.mods.xml'
            if not os.path.exists(mods_file):
                errors.append('Missing mods file on disk for item: ' + do_id)
        elif type == 'image':
            if not line['item_files']:
                errors.append('Missing data in files field for item: ' + do_id)

        # cataloged items should have an voyager id and existing marc-xml file
        if type in ['text - cataloged', 'newspaper - cataloged']:
            if not item_dict['voyager_id']:
                errors.append('Missing data in voyager_id field for item: ' + do_id)
            marcxml_file = '/usr/local/dlxs/prep/m/marcxml/' + item_dict['voyager_id'] + '.marcxml.xml'
            if not os.path.exists(marcxml_file):
                errors.append('Missing marcxml file on disk for item: ' + do_id)

        if len(errors) > 0:
            error_string = '\n'.join(errors)
            raise Exception(error_string)
        else:
            return
    except KeyError as ke:
        error_string = 'Missing expected field in CSV header: ' + str(ke)
        raise Exception(error_string)
    except Exception as e:
        error_string = 'Bad item data:\n' + str(e)
        raise Exception(error_string)

def handle_local_data_fields(cleaned_data, line=None, item=None, batch=None):
    """do stuff with locally-defined data fields in the batch data file"""
    if line:
        do_id = line['id']
        item = workflow.core.models.Item.objects.get(do_id=do_id)
    local_item = Local_Item(item=item)
    local_item.copyright_status='unknown'
    local_item.publication_status='unknown'
    if batch:
        local_item.apply_batch_defaults(batch)
    local_item.save()

    
def handle_local_csv_items(batch, data_file):
    destination = open('/tmp/' + data_file.name, 'wb+')
    for chunk in data_file.chunks():
        destination.write(chunk)
    destination.close()
    csv_data = csv.DictReader(open('/tmp/' + data_file.name, 'rU'))
    validate_csv(batch, csv_data)
    csv_data2 = csv.DictReader(open('/tmp/' + data_file.name, 'rU'))
    for line in csv_data2:
        if not 'copyright_status' in line.keys():
            line['copyright_status'] = 'unknown'
        if not 'publication_status' in line.keys():
            line['publication_status'] = 'unknown'
        line['type'] = batch.type.id
        line['primary_collection'] = batch.collection.id
        line['do_id'] = line['id']
        line['name'] = drlutils.text.utils.shorten_string(line['name'], 250)
        form = Local_Item_Form(line)
        if form.is_valid():
            this_item = form.save()
        else:
            raise Exception(form.errors)
        handle_local_item_extras(this_item, batch)
        if 'files' in csv_data.fieldnames:
            handle_files(this_item, line['files'])
    os.remove('/tmp/' + data_file.name)


def handle_local_item_extras(item, batch):
    workflow.core.createbatch.handle_item_extras(item, batch)
    drlutils.collection_building.utils.create_collection_building_item_status(item.do_id, batch.collection.c_id)
    
