from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response
from models import Category, Page, UserProfile
from forms import CategoryForm, PageForm, UserForm, UserProfileForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from datetime import datetime
from bing_search import run_query

# Create your views here.

def index(request):
    #return HttpResponse('Rango says hello world!<br/><a href="/rango/about/">About Page</a>')
    context = RequestContext(request)

    page_list = Page.objects.order_by('-views')[:5]
    context_dict = {'cat_list': get_category_list(), 'pages': page_list}

    if request.session.get('last_visit'):
        last_visit = request.session.get('last_visit')
        visits = request.session.get('visits', 0)

        if (datetime.now() - datetime.strptime(last_visit[:-7], '%Y-%m-%d %H:%M:%S')).days > 0:
            request.session['visits'] = visits + 1
            request.session['last_visit'] = str(datetime.now())
    else:
        request.session['last_visit'] = str(datetime.now())
        request.session['visits'] = 1

    return render_to_response('rango/index.html', context_dict, context)


def about(request):
    context = RequestContext(request)

    context_dict = {'cat_list': get_category_list(), 'visits': request.session.get('visits', 0)}

    if request.session.get('last_visit'):
        context_dict['last_visit'] = datetime.strptime(request.session.get('last_visit')[:-7], '%Y-%m-%d %H:%M:%S')

    return render_to_response('rango/about.html', context_dict, context)

def category(request, category_name_url):
    context = RequestContext(request)
    category_name = decode_category_url(category_name_url)
    context_dict = {'cat_list': get_category_list(), 'category_name': category_name, 'category_name_url': category_name_url}

    try:
        category = Category.objects.get(name=category_name)
        pages = Page.objects.filter(category=category)
        context_dict['pages'] = pages
        context_dict['category'] = category
    except Category.DoesNotExist:
        pass
    else:
        if request.method == 'POST':
            query = request.POST['query'].strip()
            context_dict['result_list'] = run_query(query)
            context_dict['search_value'] = query
        else:
            context_dict['search_value'] = category_name


    return render_to_response('rango/category.html', context_dict, context)

@login_required
def like_category(request):
    context = RequestContext(request)
    cat_id = None
    if request.method == 'GET':
        cat_id = request.GET['category_id']

    if cat_id:
        category = Category.objects.get(id=int(cat_id))
        if category:
            category.likes += 1
            category.save()

    return HttpResponse(category.likes)


@login_required
def add_category(request):
    context = RequestContext(request)

    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid:
            form.save(commit=True)
            return index(request)
        else:
            print(form.errors)
    else:
        form = CategoryForm()

    return render_to_response('rango/add_category.html', {'cat_list': get_category_list(), 'form': form}, context)

@login_required
def add_page(request, category_name_url):
    context = RequestContext(request)

    category_name = decode_category_url(category_name_url)
    if request.method == 'POST':
        form = PageForm(request.POST)

        if form.is_valid():
            page = form.save(commit=False)
            try:
                cat = Category.objects.get(name=category_name)
                page.category =  cat
            except Category.DoesNotExist:
                return render_to_response('rango/add_category.html', {}, context)

            page.views = 0
            page.save()

            return category(request, category_name_url)
        else:
            print(form.errors)
    else:
        form = PageForm()

    return render_to_response('rango/add_page.html', {
       'cat_list': get_category_list(),
       'category_name_url': category_name_url,
       'category_name': category_name,
       'form': form
        },
        context)

def register(request):
    context = RequestContext(request)

    registered = False

    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            user.set_password(user.password)
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user

            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            profile.save()
            registered = True
        else:
            print(user_form.errors, profile_form.errors)
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    return render_to_response(
        'rango/register.html',
        {
            'cat_list': get_category_list(),
            'user_form': user_form,
            'profile_form': profile_form,
            'registered': registered
        },
        context
    )

def user_login(request):
    context = RequestContext(request)

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)

        if user:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect('/rango/')
            else:
                return HttpResponseRedirect('Your rango account is disabled')
        else:
            print('Invalid login details : {0} {1}'.format(username, password))
            return HttpResponse('Invalid login details supplied.')
    else:
        return render_to_response('rango/login.html', {'cat_list': get_category_list()}, context)

@login_required
def profile(request):
    context = RequestContext(request)
    context_dict = {'cat_list': get_category_list()}
    try:
        context_dict['profile'] = UserProfile.objects.get(user=request.user)
    except:
        pass

    return render_to_response('rango/profile.html', context_dict, context)

@login_required
def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/rango/')

@login_required
def restricted(request):
    return HttpResponse('Since you\'re login in, you can see this text!')

def search(request):
    context = RequestContext(request)
    result_list = []

    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            result_list = run_query(query)

    return render_to_response('rango/search.html', {'cat_list': get_category_list(), 'result_list': result_list}, context)

def track_url(request):
    context = RequestContext(request)
    if request.method == 'GET' and 'page_id' in request.GET:
        try:
            page = Page.objects.get(id=request.GET['page_id'])
            page.views += 1
            page.save()
            return redirect(page.url)
        except Page.DoesNotExist:
            pass

    return redirect('/rango/')

def encode_category_url(category_name):
    return category_name.replace(' ', '_')

def decode_category_url(category_url):
    return category_url.replace('_', ' ')

def get_category_list(max_results=0, starts_with=''):
    category_list = []
    if starts_with:
        category_list = Category.objects.filter(name__istartswith=starts_with).order_by('-likes')
    else:
        category_list = Category.objects.all()

    if max_results> 0:
        if(len(category_list) > max_results):
            cat_list = category_list[:max_results]

    for category in category_list:
        category.url = encode_category_url(category.name)

    return category_list

def suggest_category(request):
    context = RequestContext(request)
    starts_with = ''
    if request.method == 'GET':
        starts_with = request.GET['suggestion']

    cat_list = get_category_list(8, starts_with)
    return render_to_response('rango/category_list.html', {'cat_list': cat_list}, context)

@login_required
def auto_add_page(request):
    context = RequestContext(request)
    context_dict = {}
    if request.GET:
        cat_id = request.GET['cat_id']
        url = request.GET['url']
        title = request.GET['title']
        if cat_id:
            category = Category.objects.get(id=int(cat_id))
            Page.objects.get_or_create(category=category, title=title, url=url)
            pages = Page.objects.filter(category=category).order_by('-views')
            context_dict['pages'] = pages

    return render_to_response('rango/page_list.html', context_dict, context)
