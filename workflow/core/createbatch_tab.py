from workflow.wfweb.models import *

def create_batch_from_form(cleaned_data, data_file):
	"""Process passed form data to create batch and item records in database."""
	batch_id = cleaned_data['id']
	type = cleaned_data['type']
	collection = cleaned_data['collection']
	property_owner = cleaned_data['property_owner']
	description = cleaned_data['description']
	actions = cleaned_data['actions'].split(',')
	# create a record for the Batch object
	b = Batch(id=batch_id, collection=collection, type=type, property_owner=property_owner, description=description)
	b.save()

	# for each line in the file, create item records.  For each item, create item_actions_status records
	item_count = 0
	for line in data_file.__iter__():
		line = line.rstrip()
		item_id, item_name = line.split('\t')
		batch = Batch.objects.get(pk=batch_id)
		item = Item(id=item_id, name=item_name, type=type, property_owner=property_owner)
		item.save()
		collection_item = Collection_Item(item=item, collection=collection)
		collection_item.save()
		batch_item = Batch_Item(item=item, batch=batch)
		batch_item.save()
		ics = Item_Current_Status(item=item)
		item_count = item_count + 1
		for i in range(len(actions)):
			item = Item.objects.get(pk=item_id)
			action = Action.objects.get(pk=actions[i])
			ias = Item_Actions_Status(item=item, action=action, order=i, ready=False, complete=False)
			if i == 0:
				ias.ready = True  # set the first action to "ready"
				ics.ready_action = ias.action	
			ias.save()
		ics.save()
	
	# add the item count
	b = Batch.objects.get(pk=batch_id)		
	b.item_count = item_count
	b.save()
