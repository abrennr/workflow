from django import template

register = template.Library()
# truncate after a certain number of characters
def truncate_chars(value, arg):
	if len(value) < arg:
        	return value
	else:
        	return value[:arg] + '...'

register.filter('truncate_chars', truncate_chars)

