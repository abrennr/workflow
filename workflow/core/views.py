from django.template import Context, loader, RequestContext
from workflow.core.models import *
from workflow.core.createbatch import handle_csv_items, handle_item_extras, handle_files 
from workflow.core.createsequence import create_sequence_from_form
from workflow.core.transaction import record_transaction
from workflow.core.status import set_status 
from workflow.core.filters import BatchFilter, ItemFilter 
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError
from django.shortcuts import get_object_or_404, render_to_response
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.core import serializers
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
import datetime


LIST_HEADERS = (
    ('Item ID', 'item__id'),
    ('name', 'item__name'),
    ('ready for', 'ready_action'),
    ('last action', 'last_transaction__description'),
    ('when', 'last_transaction__timestamp'),
    ('who', 'last_transaction__user__first_name'),
)

def get_facet_block(items_queryset, facet_fields, request):
    facet_block = {}
    for facet_field in facet_fields:
        this_facet_dict = {}
        # if there's currently a facet selected, add an option to clear
        if facet_field in request.GET.keys() and request.GET[facet_field]:
            this_query_dict = request.GET.copy()
            this_query_dict.__setitem__(facet_field, '')
            this_facet_dict['[clear selection]'] = this_query_dict.urlencode()
        # get the distinct values for this field in the queryset
        values_query_set = items_queryset.order_by().values(facet_field).distinct()
        for value_dict in values_query_set:
            this_value = value_dict[facet_field]
            # get the count of matching objects
            kwargs = { facet_field:this_value }
            count = items_queryset.filter(**kwargs).count()
            # get the label for the matching field value.  In order to handle related object fields
            # that would otherwise be id values, we do the __unicode__ method to get the name
            try:
                label = items_queryset.order_by().filter(**kwargs)[0].__getattribute__(facet_field).__unicode__()
            except:
                label = 'None'
            this_query_dict = request.GET.copy()
            this_query_dict.__setitem__(facet_field, this_value)
            key = '%s (%s)' % (label, count)
            this_facet_dict[key] = this_query_dict.urlencode()
        facet_block[facet_field] = this_facet_dict
    return facet_block

def get_humanized_bytes(bytes):
    if bytes < 1048576:
        return str(bytes/1024) + ' KB'
    elif bytes < 1073741824:
        return str(bytes/1048576) + ' MB'
    else:
        return str(bytes/1073741824) + ' GB'

def sort_objects_by_name(objects):
    obj_dict = {}
    sorted_list = []
    for obj in objects:
        obj_dict[obj.name] = obj
    order = obj_dict.keys()
    order.sort()
    for o in order:
        sorted_list.append(obj_dict[o])
    return sorted_list

def sort_collections(objects):
    obj_dict = {}
    sorted_list = []
    for obj in objects:
        obj_dict[obj.c_id] = obj
    order = obj_dict.keys()
    order.sort()
    for o in order:
        sorted_list.append(obj_dict[o])
    return sorted_list

def sort_items(objects):
    obj_dict = {}
    sorted_list = []
    for obj in objects:
        obj_dict[obj.do_id] = obj
    order = obj_dict.keys()
    order.sort()
    for o in order:
        sorted_list.append(obj_dict[o])
    return sorted_list

def sort_objects_by_id(objects):
    obj_dict = {}
    sorted_list = []
    for obj in objects:
        obj_dict[obj.id] = obj
    order = obj_dict.keys()
    order.sort()
    for o in order:
        sorted_list.append(obj_dict[o])
    return sorted_list

def get_paged_items(items, request):
    paginator = Paginator(items, 25)
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1
    try:
        return paginator.page(page)
    except (EmptyPage, InvalidPage):
        return paginator.page(paginator.num_pages)

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse('workflow.core.views.main'))

def item(request):
    items = Item.objects.all() 
    paged_items = get_paged_items(items, request)
    t = loader.get_template('core/item.html')
    c = RequestContext(request, {
        'items': paged_items,
    })
    return HttpResponse(t.render(c))

def get_item(request):
    items = ItemFilter(request.GET, queryset=Item.objects.all()).qs
    if 'q' in request.GET:
        query = request.GET['q']
        if request.GET['lookup'] == 'identifier':
            items =  items.filter(do_id__icontains=query)
        elif request.GET['lookup'] == 'name':
            items =  items.filter(name__icontains=query)

        if items.count() == 1:
            return HttpResponseRedirect(reverse('workflow.core.views.item_detail', args=[items[0].do_id]))

    paged_items = get_paged_items(items, request)
    facet_block = get_facet_block(items, ['primary_collection', 'type', 'property_owner'], request)
    t = loader.get_template('core/item.html')
    c = RequestContext(request, {
        'items': paged_items,
        'facet_block': facet_block,
    })
    return HttpResponse(t.render(c))

def transaction():
    pass    

def item_detail(request, item_id):
    item = Item.objects.get(do_id=item_id)
    transaction_list = item.transaction_set.all()
    status_list = Item_Actions_Status.objects.filter(item=item).order_by('order')
    problems_list = item.problem_set.all()
    file_list = Item_File.objects.filter(item=item).order_by('name')
    collections = Collection.objects.filter(collection_item__item__id=item.id) 
    batches = Batch.objects.filter(batch_item__item__id=item.id) 
    t = loader.get_template('core/item_detail.html')
    c = RequestContext(request, {
        'item': item,
    'transaction_list': transaction_list,
    'status_list': status_list,
    'file_list': file_list,
    'problems_list': problems_list,
    'batches': batches,
    'collections': collections,
    })
    return HttpResponse(t.render(c))

def transactions(request):
    transactions = get_paged_items(Transaction.objects.order_by('timestamp').reverse(), request)
    t = loader.get_template('core/transactions.html')
    c = RequestContext(request, { 'items': transactions, })
    return HttpResponse(t.render(c))

@login_required
def main(request):
    item_count = Item.objects.count()
    file_count = Item_File.objects.count()
    batch_count = Batch.objects.count()
    active_batch_count = Batch.objects.filter(active=True).count()
    coll_count = Collection.objects.count()    
    last_five_transactions = Transaction.objects.order_by('timestamp').reverse()[:5]
    t = loader.get_template('core/main.html')
    c = RequestContext(request, {
    'items': item_count,
    'files': file_count,
    'batches': batch_count,
    'active_batches': active_batch_count,
    'colls': coll_count,
    'last_five': last_five_transactions,
    })
    return HttpResponse(t.render(c))

def reports(request):
    t = loader.get_template('core/reports.html')
    c = RequestContext(request)
    return HttpResponse(t.render(c))

def admin(request):
    t = loader.get_template('core/admin_menu.html')
    c = RequestContext(request)
    return HttpResponse(t.render(c))

def batch_detail(request, batch_name, new="False", order='id'):
    batch = Batch.objects.get(name=batch_name)
    f = ItemFilter(request.GET, queryset=Item_Current_Status.objects.filter(item__batch_item__batch=batch.id))
    actions = batch.get_item_actions() 
    problems = batch.get_problem_item_count() 
    paged_items = get_paged_items(f.qs, request)
    for p_i in paged_items.object_list:
        p_i.file_count = len(Item_File.objects.filter(item=p_i.item))
        if p_i.file_count > 0:
            p_i.first_file = Item_File.objects.filter(item=p_i.item).order_by('name')[0]
    t = loader.get_template('core/batch_detail.html')
    c = RequestContext(request, {
        'batch': batch,
        'new': new,
        'items': paged_items,
        'action_facet': actions,
        'problem_facet': problems,
        'filter': f,

    })
    return HttpResponse(t.render(c))

def collection(request):
    collections = sort_collections(Collection.objects.all()) 
    for c in collections:
        c.item_count = Collection_Item.objects.filter(collection=c).count()
        c.batch_count = Batch.objects.filter(collection=c).count()
        c.ready_actions = c.get_ready_actions() 
    t = loader.get_template('core/collection.html')
    c = RequestContext(request, {
        'collections': collections,
    })
    return HttpResponse(t.render(c))


def collection_detail(request, collection_id, order='id'):
    collection = Collection.objects.get(c_id=collection_id)
    f = ItemFilter(request.GET, queryset=Item_Current_Status.objects.filter(item__collection_item__collection=collection))
    c_count = len(Collection_Item.objects.filter(collection=collection))
    actions = collection.get_item_actions() 
    problems = collection.get_problem_item_count() 
    paged_items = get_paged_items(f.qs, request)
    c_batches = Batch.objects.filter(collection=collection).order_by('-date')
    t = loader.get_template('core/collection_detail.html')
    c = RequestContext(request, {
        'collection': collection,
        'items': paged_items,
        'c_count': c_count,
        'c_batches': c_batches,
        'action_facet': actions,
        'problem_facet': problems,
    })
    return HttpResponse(t.render(c))

def property_owner(request):
    property_owners = Property_Owner.objects.all() 
    t = loader.get_template('core/property_owner.html')
    c = RequestContext(request, {
           'property_owners': property_owners,
   })
    return HttpResponse(t.render(c))

def property_owner_detail(request, property_owner_id):
    property_owner = Property_Owner.objects.get(pk=property_owner_id)
    items = Item.objects.filter(property_owner=property_owner_id)
    paged_items = get_paged_items(items, request)
    t = loader.get_template('core/property_owner_detail.html')
    c = RequestContext(request, {
        'property_owner': property_owner,
        'items': paged_items,
    })
    return HttpResponse(t.render(c))


def item_type(request):
    item_types = Item_Type.objects.all() 
    t = loader.get_template('core/item_type.html')
    c = RequestContext(request, {
           'item_types': item_types,
   })
    return HttpResponse(t.render(c))

def item_type_detail(request, item_type_id):
    item_type = Item_Type.objects.get(pk=item_type_id)
    items = Item.objects.filter(type=item_type_id)
    paged_items = get_paged_items(items, request)
    t = loader.get_template('core/item_type_detail.html')
    c = RequestContext(request, {
        'item_type': item_type,
         'items': paged_items,
    })
    return HttpResponse(t.render(c))


def batch(request, view='active'):
    try:
      batch = Batch.objects.get(name=request.GET['batch_name'])
      return HttpResponseRedirect(reverse('workflow.core.views.batch_detail', args=(batch.id,)))
    except:
        if view == 'all':
            f = BatchFilter(request.GET, queryset=Batch.objects.all().order_by('-date'))
        else:
            f = BatchFilter(request.GET, queryset=Batch.objects.filter(active=True).order_by('-date'))
        collection_facet = [] 
        type_facet = [] 
        property_owner_facet = [] 
        for batch in f.qs:
            collection_facet.append(Collection.objects.get(pk=batch.collection.id))
            type_facet.append(Item_Type.objects.get(pk=batch.type.id))
            try:
                property_owner_facet.append(Property_Owner.objects.get(pk=batch.property_owner.id))
            except:
                pass
            batch.ready_actions = batch.get_ready_actions() 
        collection_facet = sort_collections(set(collection_facet))
        type_facet = sort_objects_by_name(set(type_facet))
        property_owner_facet = sort_objects_by_name(set(property_owner_facet))
        t = loader.get_template('core/batch.html')
        c = RequestContext(request, {
            'filter': f,
            'collection_facet': collection_facet,
            'type_facet': type_facet,
            'property_owner_facet': property_owner_facet,
        })
        return HttpResponse(t.render(c))


def batch_new(request):
    if request.method == 'POST':
        form = BatchForm(request.POST, request.FILES)
        if 'has_file' in request.POST.keys():
            form.fields['file'].required = True 
        if form.is_valid(): 
            batch = form.save()
            if 'has_file' in request.POST.keys():
                handle_csv_items(batch, request.FILES['file'])
            return HttpResponseRedirect(reverse('workflow.core.views.batch_detail', kwargs={ batch_name: batch.name, new: 'success'})) 
    else:
        form = BatchForm()
    t = loader.get_template('core/newbatch.html')
    c = RequestContext(request, { 'form' : form })
    return HttpResponse(t.render(c))


def sequence_list(request):
    seqs = Workflow_Sequence.objects.all().order_by('name')
    t = loader.get_template('core/sequence_list.html')
    c = RequestContext(request, { 'seqs' : seqs })
    return HttpResponse(t.render(c))


def sequence_new(request):
    if request.method == 'POST':
        form = SequenceForm(request.POST)
        if form.is_valid():
            create_sequence_from_form(form.cleaned_data)
            return HttpResponseRedirect(reverse('workflow.core.views.sequence_list')) 
    else:
        form = SequenceForm()
    actions = Action.objects.all().order_by('name')
    t = loader.get_template('core/sequence.html')
    c = RequestContext(request, { 'workflow_sequence_form' : form, 'actions' : actions })
    return HttpResponse(t.render(c))


def sequence_detail(request, sequence_id):
    if request.method == 'POST': # update of an existing sequence
        seq = Workflow_Sequence.objects.get(id=request.POST['this_id'])
        form = SequenceForm(request.POST, instance=seq)
        if form.is_valid():
            create_sequence_from_form(form.cleaned_data)
            return HttpResponseRedirect(reverse('workflow.core.view.sequence_list')) 
    else:
        seq = Workflow_Sequence.objects.get(name=sequence_id)
        form = SequenceForm(instance=seq)
    form.fields['this_id'].initial = seq.id
    seq_actions = Workflow_Sequence_Actions.objects.filter(workflow_sequence=seq).order_by('order')
    actions = Action.objects.all().order_by('name')
    t = loader.get_template('core/sequence.html')
    c = RequestContext(request, { 'workflow_sequence_form' : form, 'actions' : actions, 'sequence': seq, 'seq_actions' : seq_actions })
    return HttpResponse(t.render(c))


def setup_status_change(request):
    if request.method == 'POST':
        form = ChangeStatusSetupForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            complete = form.cleaned_data['complete']
            return HttpResponseRedirect(reverse('workflow.core.views.status_change', kwargs={ action: str(action.id), complete: str(complete)}))
    else:
        form = ChangeStatusSetupForm()            
    
    t = loader.get_template('core/status_change_setup.html')
    c = RequestContext(request, { 'form' : form })
    return HttpResponse(t.render(c))


def status_change(request, action, complete):
    item = None
    if request.method == 'POST':
        form = ChangeStatusForm(request.POST)
        if form.is_valid():
            item = Item.objects.get(do_id=form.cleaned_data['item'])
            user = User.objects.get(pk=request.POST['user'])
            act = Action.objects.get(pk=action)
            set_status(item, act, user, complete)
            form = ChangeStatusForm()
    else:
        form = ChangeStatusForm()            
    a = Action.objects.get(pk=action)
    t = loader.get_template('core/status_change.html')
    c = RequestContext(request, { 'form' : form, 'action' : a, 'complete' : complete, 'item' : item })
    return HttpResponse(t.render(c))

def batch_active_change(request, batch_id):
    batch = Batch.objects.get(id=batch_id)
    if batch.active:
        batch.active = False
    else:
        batch.active = True
    batch.save()
    return HttpResponseRedirect(reverse('workflow.core.views.batch'))

def batch_status_change(request, batch_name):
    batch = Batch.objects.get(name=batch_name)
    if request.method == 'POST':
        form = BatchChangeStatusForm(request.POST)
        if form.is_valid():
            action = Action.objects.get(pk=form.cleaned_data['action'])
            user = User.objects.get(pk=request.POST['user'])    
            complete = form.cleaned_data['complete']
            change_items = []
            if complete == 'True':    
                change_items = Item.objects.filter(batch_item__batch=batch, item_current_status__ready_action=action)
            elif complete == 'False':
                change_items = Item.objects.filter(batch_item__batch=batch, item_actions_status__action=action)
            for item in change_items:
                set_status(item, action, user, complete)
            return HttpResponseRedirect(reverse('workflow.core.views.batch_detail', args=[str(batch.name)]))
    form = BatchChangeStatusForm()
    t = loader.get_template('core/batch_status_change.html')
    c = RequestContext(request, { 'form' : form, 'batch' : batch, 'actions' : batch.get_item_actions() })
    return HttpResponse(t.render(c))

def batch_add_items(request, batch_name):    
    batch = Batch.objects.get(name=batch_name)
    if request.method == 'POST':
        form = BatchFileForm(request.POST, request.FILES)
        if form.is_valid():
            handle_csv_items(batch, request.FILES['file'])
            return HttpResponseRedirect(reverse('workflow.core.views.batch_detail', kwargs={ batch_name: batch.name, new: 'success'})) 
    else:
        form = BatchFileForm()
    t = loader.get_template('core/add_to_batch.html')
    c = RequestContext(request, { 'batch' : batch, 'form' : form })
    return HttpResponse(t.render(c))
    
def batch_add_single_item(request, batch_name):    
    batch = Batch.objects.get(name=batch_name)
    if request.method == 'POST':
        item_form = ItemForm(request.POST)
        if item_form.is_valid():
            new_item = item_form.save()
            handle_item_extras(new_item, batch) 
            if item_form.cleaned_data['item_files']:
                handle_files(new_item, item_form.cleaned_data['item_files'])
        if request.POST.has_key('_addanother'):
            return HttpResponseRedirect(reverse('workflow.core.views.batch_add_single_item', args=[batch_name]))
        else:
            return HttpResponseRedirect(reverse('workflow.core.views.batch_detail', args=[batch_name]))
    else:
        this_item = Item()
        this_item.inherit_from_batch(batch)
        item_form = ItemForm(instance=this_item)
    errors = ''
    t = loader.get_template('core/add_single_item_to_batch.html')
    c = RequestContext(request, { 'batch' : batch, 'item_form' : item_form })
    return HttpResponse(t.render(c))

def status_ready(request, action):
    ics = Item_Current_Status.objects.filter(ready_action=action)
    json_serializer = serializers.get_serializer("json")()
    response = HttpResponse()
    json_serializer.serialize(ics, ensure_ascii=False, stream=response)
    return response

def problem_new(request, item_id):
    if request.method == 'POST':
        form = ReportProblemForm(request.POST)
        if form.is_valid():
            this_item = Item.objects.get(do_id=form.cleaned_data['item'])
            p = Problem(item=this_item, user_reported=request.user, description=form.cleaned_data['description'])
            p.save()
            record_transaction(None, this_item, request.user, 'preport')
            ics = Item_Current_Status.objects.get(item=this_item)
            ics.has_problem = True
            ics.save()
            return HttpResponseRedirect(reverse('workflow.core.views.item_detail', args=[form.cleaned_data['item']]))
    else: 
        item = Item.objects.get(do_id=item_id)
        form = ReportProblemForm()
    
    t = loader.get_template('core/report_problem.html')
    c = RequestContext(request, { 'form' : form, 'item': item })
    return HttpResponse(t.render(c))


def problem_detail(request, problem_id):
    if request.method == 'POST':
        form = ProblemForm(request.POST)
        if form.is_valid() and form.cleaned_data['resolved']:    
            p = Problem.objects.get(pk=problem_id)
            p.resolved = True
            p.user_resolved = request.user
            p.notes_resolved = form.cleaned_data['notes_resolved']
            p.time_resolved = datetime.datetime.now()
            p.save()
            record_transaction(None, p.item, request.user, 'presolve')
            if Problem.objects.filter(item=p.item, resolved=False).count() == 0:
                ics = Item_Current_Status.objects.get(item=p.item)
                ics.has_problem = False
                ics.save()
            return HttpResponseRedirect(reverse('workflow.core.views.item_detail', args=[p.item.do_id]))

    p = Problem.objects.get(pk=problem_id)
    form = ProblemForm(instance=p)
    t = loader.get_template('core/problem_detail.html')
    c = RequestContext(request, { 'form' : form, 'problem': p})
    return HttpResponse(t.render(c))

def item_file(request, item_id, file_name=None):
    if request.method == 'POST':
        form = ItemFileForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('workflow.core.views.item_detail', args=[item_id]))
    else: 
        this_item = Item.objects.get(do_id=item_id)
        if file_name:
            item_file = Item_File.objects.get(item=this_item, name=file_name)
            form = ItemFileForm(instance=item_file)
        else:
            form = ItemFileForm({'item': this_item.id})
    t = loader.get_template('core/item_file.html')
    c = RequestContext(request, { 'form' : form, 'item' : item_id })
    return HttpResponse(t.render(c))

