from models import *
from transaction import record_transaction

def set_status(item, action, user, status):
	if status == "True":
		item.set_action_complete(action)
		item.set_next_action_ready(action)
	elif status == "False":
		item.set_action_complete(action, 'False')
		item.set_action_ready(action)
	record_transaction(action, item, user, status)
	ics = Item_Current_Status.objects.get(item=item)
	try:
		ics.ready_action = Item_Actions_Status.objects.get(item=item, ready=True).action
	except:
		ics.ready_action = None
	ics.save()
