from django.db import models
from django import forms
from workflow.core.models import * 
import datetime

COPYRIGHT_STATUS_VALUES = (
    ('copyrighted', 'copyrighted'),
    ('pd', 'public domain'),
    ('pd_usfed', 'public domain - us federal document'),
    ('pd_holder', 'public domain - dedicated by rights holder'),
    ('pd_expired', 'public domain - expired copyright'),
    ('unknown', 'unknown')
)

PUBLICATION_STATUS_VALUES = (
    ('published', 'published'),
    ('unpublished', 'unpublished'),
    ('unknown', 'unknown')
) 


class Building_Action(models.Model):
    name = models.CharField(max_length=64)
    description = models.TextField()
    def __unicode__(self):
        return self.name

class Collection_Building_Actions(models.Model):
    collection = models.ForeignKey(Collection)
    action = models.ForeignKey(Building_Action)
    order = models.IntegerField()
    item_ready_count = models.IntegerField()
    def __unicode__(self):
        return ' - '.join([self.collection.c_id, str(self.order), self.action.name])

class Collection_Building_Item_Status(models.Model):
    item = models.ForeignKey(Collection_Item)
    action = models.ForeignKey(Building_Action)
    order = models.IntegerField()
    timestamp = models.DateTimeField(blank=True, null=True)
    def get_next(self):
        try:
            next_order = self.order + 1
            return Collection_Building_Item_Status.objects.get(order=next_order, item=self.item)
        except:
            return False
    def is_outdated(self):
        if not self.timestamp:
            return True
        elif self.timestamp < Item_Current_Status.objects.get(item=self.item.item).last_transaction.timestamp:
            return True
        else:
            return False
    def set_timestamp(self, t=datetime.datetime.now()):
        self.timestamp = t
        self.save()
    def prerequisites_complete(self, prerequisite_action_names):
        for action_name in prerequisite_action_names:
            if Collection_Building_Item_Status.objects.get(item=self.item, action__name=action_name).is_outdated():
                return False
        return True
        
class Fedora_Site(models.Model):
    name = models.CharField(max_length=255)
    pid = models.CharField(max_length=255, unique=True)
    def __unicode__(self):
        return self.name

class Fedora_Collection(models.Model):
    name = models.CharField(max_length=255)
    page_name = models.CharField(max_length=255)
    pid = models.CharField(max_length=255, unique=True)
    sites = models.ManyToManyField(Fedora_Site)
    def __unicode__(self):
        return self.name

class Local_Batch(Batch):
    priority = models.IntegerField(blank=True, null=True)
    source_id = models.CharField('source identifier', max_length=255, null=True, blank=True)
    is_request = models.BooleanField('is a request?', default=False)
    requestor = models.CharField(max_length=255, blank=True, null=True)
    request_due_date = models.DateField(blank=True, null=True)
    condition_handling = models.TextField(blank=True, null=True)
    file_type = models.CharField(max_length=255, blank=True, null=True)
    file_naming = models.CharField('file naming scheme', max_length=255, blank=True, null=True)
    resolution_ppi = models.CharField('image resolution in ppi', max_length=255, blank=True, null=True)
    image_type_bit_depth = models.CharField('image color type and bit depth', max_length=255, blank=True, null=True)
    target_size = models.CharField('output target size', max_length=255, blank=True, null=True)
    edge_treatment = models.TextField('page edge treatment', max_length=255, blank=True, null=True)
    use_color_target = models.BooleanField('use a color target?', default=False)
    blank_missing_treatment = models.TextField('blank and missing page treatment', max_length=255, blank=True, null=True)
    image_editing_treatment = models.TextField(max_length=255, blank=True, null=True)
    structural_metadata_treatment = models.TextField(max_length=255, blank=True, null=True)
    voyager_id = models.CharField('default voyager id', max_length=255, blank=True, null=True)
    ead_id = models.CharField('default EAD id', max_length=255, blank=True, null=True)
    copyright_status = models.CharField('default copyright status', max_length=255, choices=COPYRIGHT_STATUS_VALUES, blank=True, null=True)
    publication_status = models.CharField('default publication status', max_length=255, choices=PUBLICATION_STATUS_VALUES, blank=True, null=True)
    copyright_holder_name = models.TextField('default copyright holder name', blank=True, null=True)
    permission_notes = models.TextField('default permission notes', blank=True, null=True)
    depositor = models.CharField('default depositor', max_length=255, blank=True, null=True)
    type_of_resource = models.CharField('default type of resource', max_length=255, blank=True, null=True)
    genre = models.CharField('default genre', max_length=255, blank=True, null=True)

    def __unicode__(self):
        return self.name


class Local_Item(Item):
    enumeration = models.CharField(max_length=255, blank=True, null=True)
    date_issued = models.CharField(max_length=21, blank=True, null=True)
    online_pub_date = models.DateField(auto_now=False, blank=True, null=True,)
    copyright_status = models.CharField(max_length=255, choices=COPYRIGHT_STATUS_VALUES)
    publication_status = models.CharField(max_length=255, choices=PUBLICATION_STATUS_VALUES)
    copyright_holder_name = models.CharField(max_length=255, blank=True, null=True)
    permission_notes = models.CharField(max_length=255, blank=True, null=True)
    voyager_id = models.CharField(max_length=255, blank=True, null=True)
    ead_id = models.CharField(max_length=255, blank=True, null=True)
    depositor = models.CharField(max_length=255, blank=True, null=True)
    type_of_resource = models.CharField(max_length=255, blank=True, null=True)
    genre = models.CharField(max_length=255, blank=True, null=True)
    thumb_filename = models.CharField(max_length=255, blank=True, null=True)
    digitization_responsibility = models.CharField(max_length=255, blank=True, null=True)
    digitization_date = models.CharField(max_length=255, blank=True, null=True)
    fedora_collections = models.ManyToManyField(Fedora_Collection, blank=True, null=True)
    fedora_sites = models.ManyToManyField(Fedora_Site, blank=True, null=True)

    def __unicode__(self):
        return self.name

    def inherit_from_batch(self, batch, clobber=False):
        super(Local_Item, self).inherit_from_batch(batch, clobber)
        if clobber or not self.copyright_status:
            self.copyright_status = batch.copyright_status
        if clobber or not self.publication_status:
            self.publication_status = batch.publication_status
        if clobber or not self.copyright_holder_name:
            self.copyright_holder_name = batch.copyright_holder_name
        if clobber or not self.permission_notes:
            self.permission_notes = batch.permission_notes
        if clobber or not self.voyager_id:
            self.voyager_id = batch.voyager_id
        if clobber or not self.property_owner:
            self.property_owner = batch.property_owner
        if clobber or not self.ead_id:
            self.ead_id = batch.ead_id
        if clobber or not self.depositor:
            self.depositor = batch.depositor
        if clobber or not self.type_of_resource:
            self.type_of_resource = batch.type_of_resource
        if clobber or not self.genre:
            self.genre = batch.genre 

class DRL_Collection(models.Model):
    collection = models.ForeignKey(Collection, unique=True) 
    sort_field = models.CharField(max_length=255)
    derivative_type = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    item_count = models.IntegerField()
    completed_item_count = models.IntegerField()
    def __unicode__(self):
        return self.collection.name

class Dlxs_Image_Config(models.Model):
    collection = models.ForeignKey(Collection)
    name = models.CharField(max_length=255)
    abbreviation = models.CharField(max_length=255)
    metaname = models.CharField(max_length=255)
    admin_mapping = models.CharField(max_length=255)

class Metadata_Maps(models.Model):
    collection = models.ForeignKey(Collection)
    schema = models.CharField(max_length=64)
    mapping = models.TextField()
    
    def __unicode__(self):
        return ('%s - %s' % (self.collection.c_id, self.schema))

class Source_Collection(models.Model):
    source_id = models.CharField(max_length=255)
    digital_collection_id = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    full_citation = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    fedora_collection = models.ForeignKey(Fedora_Collection)
    def __unicode__(self):
        return self.name


class CollectionActionsForm(forms.ModelForm):
    class Meta:
        model = Collection_Building_Actions 

class Local_Item_Form(forms.ModelForm):
    class Meta:
        model = Local_Item
    item_files = forms.CharField(required=False)

class Local_Item_To_Batch_Form(forms.ModelForm):
    class Meta:
        model = Local_Item
        fields = ['do_id', 'name', 'enumeration', 'date_issued', 'primary_collection', 'property_owner', 'copyright_status', 'publication_status', 'copyright_holder_name', 'permission_notes', 'type', 'voyager_id', 'ead_id', 'depositor', 'type_of_resource', 'genre', 'fedora_sites', 'fedora_collections']
    item_files = forms.CharField(required=False)

class Local_Batch_Form(forms.ModelForm):
    class Meta:
        model = Local_Batch
    collection = forms.ModelChoiceField(queryset=Collection.objects.all().order_by('c_id'))
    property_owner = forms.ModelChoiceField(queryset=Property_Owner.objects.all().order_by('name'))
    sequence = forms.ModelChoiceField(queryset=Workflow_Sequence.objects.all().order_by('name'))
    has_file = forms.BooleanField(initial=True,required=False)
    file = WorkflowBatchFileCsv(required=False)

