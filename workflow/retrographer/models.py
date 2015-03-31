from django.db import models

# Create your models here.
class Tag(models.Model):
	photo_id = models.CharField(max_length=255)
	retrographer_id = models.IntegerField()
	user_id = models.IntegerField()
	user_first_name = models.CharField(max_length=255)
	lat = models.FloatField()
	long = models.FloatField()
	heading = models.FloatField(null=True, blank=True)
	pitch = models.FloatField(null=True, blank=True)
	zoom = models.FloatField(null=True, blank=True)
	timestamp = models.DateTimeField()
	is_used = models.BooleanField()
