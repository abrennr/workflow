from django.db import models
import datetime

# Create your models here.
class Collection(models.Model):
    title = models.CharField(max_length=255)
    map_purpose = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    theme_keywords = models.TextField(blank=True, null=True)
    
    def __unicode__(self):
        return self.title

class Reference_Layer(models.Model):
    title = models.CharField(max_length=255, blank=True, null=True)
    creator = models.CharField(max_length=255, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    pub_place = models.CharField(max_length=255, blank=True, null=True) 
    pub_date = models.CharField(max_length=255, blank=True, null=True) 
    content_date = models.CharField(max_length=255, blank=True, null=True)
    content_current_ref = models.CharField("Content Date Currentness Reference", max_length=255, blank=True, null=True)
    data_present = models.CharField(max_length=255, blank=True, null=True)
    scale_den = models.FloatField(blank=True, null=True)
    citabbrev = models.CharField(max_length=255, blank=True, null=True)
    source_media = models.CharField(max_length=255, blank=True, null=True)
    
    def __unicode__(self):
        return self.citabbrev

    class Meta:
        ordering = ["title"]
        verbose_name = "Reference Layer"
        verbose_name_plural = "Reference Layers"

class Volume(models.Model):
    title = models.TextField()
    creator = models.CharField(max_length=255, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    pub_place = models.CharField(max_length=255, blank=True, null=True)
    date = models.CharField(max_length=255, blank=True, null=True)
    subject = models.CharField(max_length=255, blank=True, null=True)
    content_date = models.CharField(max_length=255, blank=True, null=True)
    content_current_ref = models.CharField(max_length=255, blank=True, null=True)

    def __unicode__(self):
        return '%s, %s' % (self.date, self.title)

class Map_Sheet(models.Model):
    do_id = models.CharField("digital object identifier", unique=True, max_length=255)
    title = models.CharField(max_length=255)
    creator = models.CharField(max_length=255, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    pub_place = models.CharField("publication place", max_length=255, blank=True, null=True)
    date = models.CharField(max_length=255, blank=True, null=True)
    volume = models.ForeignKey(Volume, blank=True, null=True)
    subject = models.CharField(max_length=255, blank=True, null=True)
    index_map = models.CharField(max_length=255, blank=True, null=True)
    collection = models.ForeignKey(Collection, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    title_owner = models.TextField(blank=True, null=True)
    municipality = models.CharField(max_length=255, blank=True, null=True)
    ward_name = models.CharField(max_length=255, blank=True, null=True)
    streets = models.TextField(blank=True, null=True)
    other_features = models.TextField(blank=True, null=True)
    theme_keywords = models.TextField(blank=True, null=True)
    place_keywords = models.TextField(blank=True, null=True)
    dimension = models.CharField(max_length=255, blank=True, null=True)
    filename = models.CharField(max_length=255, blank=True, null=True)
    scale = models.CharField(max_length=255, blank=True, null=True)
    scale_den = models.CharField("scale denominator", max_length=255, blank=True, null=True)
    metadata_compl = models.CharField("metadata complete", max_length=255, blank=True, null=True)
    ordering_info = models.CharField(max_length=255, blank=True, null=True)
    zip_data = models.CharField(max_length=255, blank=True, null=True)
    rights = models.CharField(max_length=255, blank=True, null=True)
    content_date = models.CharField(max_length=255, blank=True, null=True)
    content_current_ref = models.CharField("Content Date Currentness Reference", max_length=255, blank=True, null=True)

    
    def __unicode__(self):
        return '%s - %s' % (self.do_id, self.title)

    class Meta:
        ordering = ["do_id"]
        verbose_name = "Map Sheet"
        verbose_name_plural = "Map Sheets"


class Georeferenced_Map_Sheet(models.Model):
    do_id = models.CharField("digital object identifier", unique=True, max_length=255)
    title = models.CharField(max_length=255)
    date = models.DateField(blank=True, null=True)
    map_sheet = models.ForeignKey(Map_Sheet)
    reference_layer = models.ForeignKey(Reference_Layer)
    scale = models.CharField(max_length=255, blank=True, null=True)
    zip_data_gis = models.CharField(max_length=255, blank=True, null=True)

    def __unicode__(self):
        return '%s - %s' % (self.do_id, self.title)
    
    class Meta:
        verbose_name = "Georeferenced Map Sheet"
        verbose_name_plural = "Georeferenced Map Sheets"
