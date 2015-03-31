from models import *

def record_transaction(action, item, user, description):
	if action == None:
		d = description
	elif description == "True":
		d = action.name + " completed"
	elif description == "False":
		d = "reset status"
	elif description == "log":
		d = action.name + " performed"
	elif description == "preport":
		d = "problem reported"
	elif description == "presolve":
		d = "problem resolved"
	else:
		d = "unknown"

	t = Transaction(item=item, user=user, description=d)
   	t.save()
	ics = Item_Current_Status.objects.get(item=item)
	ics.last_transaction = t
	ics.save()
