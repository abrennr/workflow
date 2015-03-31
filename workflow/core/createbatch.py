import workflow.core.models
import transaction 
import csv 
import os
import sys
import drlutils.text.utils

def handle_files(this_item, file_string):
    if file_string:
        files = file_string.split(',')
        for file in files:
            file_name =  file.strip()
            i_f     = workflow.core.models.Item_File(item=this_item, name=file_name, use='MASTER')
            i_f.save()

def handle_item_actions(item, sequence):
    for sa in sequence.get_ordered_actions(): 
        ias = workflow.core.models.Item_Actions_Status(item=item, action=sa.action, order=sa.order, ready=False, complete=False)
        if sa.order == 0:
            ias.ready = True  # set the first action to "ready"
        ias.save()

def handle_batch_item(item, batch):
    batch_item = workflow.core.models.Batch_Item(batch=batch, item=item)
    batch_item.save()

def handle_collection_item(item, collection):
    collection_item = workflow.core.models.Collection_Item(item=item, collection=collection)
    collection_item.save()

def handle_item_current_status(item):
    ready_action = workflow.core.models.Item_Actions_Status.objects.get(item=item, ready=True).action
    ics = workflow.core.models.Item_Current_Status(item=item, ready_action=ready_action)
    ics.save()
    
def handle_csv_items(batch, data_file):
    destination = open('/tmp/' + data_file.name, 'wb+')
    for chunk in data_file.chunks():
        destination.write(chunk)
    destination.close()
    csv_data = csv.DictReader(open('/tmp/' + data_file.name, 'rU'))
    #workflow.wflocal.createbatch.validate_csv(batch, csv_data)
    csv_data2 = csv.DictReader(open('/tmp/' + data_file.name, 'rU'))
    for line in csv_data2:
        item_do_id = line['id']
        item_name = drlutils.text.utils.shorten_string(line['name'], 250)
        item = workflow.core.models.Item(do_id=item_do_id, name=item_name)
        item.inherit_from_batch(batch)
        item.save()
        handle_item_extras(item, batch)
        if 'files' in csv_data.fieldnames:
            handle_files(item, line['files'])
        #workflow.wflocal.createbatch.handle_local_data_fields(cleaned_data, line=line, batch=batch)
    os.remove('/tmp/' + data_file.name)

def handle_item_extras(item, batch):
    handle_collection_item(item, batch.collection)
    handle_batch_item(item, batch)
    handle_item_actions(item, batch.sequence)
    handle_item_current_status(item)
    #workflow.wflocal.createbatch.handle_local_data_fields(cleaned_data, item=item, batch=batch)
    user = workflow.core.models.User.objects.get(first_name='gort')
    transaction.record_transaction(None, item, user, 'item record created')
    batch.item_count = batch.item_count + 1
    batch.save()

