"""mgmembers_site URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from mgmembers import views as mgviews

urlpatterns = [
    url(r'^$', mgviews.IndexView.as_view(), name='index'),
    url(r'^signup/$', mgviews.SignUpView.as_view(), name='signup'),
    url(r'^signup-success/$',
        mgviews.SignUpSuccessView.as_view(),
        name='signup-success'),
    url(r'^login/$', auth_views.login,
        {'template_name': 'mgmembers/login.html'},
        name='login'),
    url(r'^logout/$', auth_views.logout,
        {'template_name': 'mgmembers/logout.html'},
        name='logout'),
    url(r'^change_password/$', mgviews.ChangePasswordView.as_view(),
        name='change-password'),
    url(r'^admin/', admin.site.urls),
    url(r'^home/$', mgviews.HomeView.as_view(), name='home'),
    url(r'^character/create/?$',
        mgviews.CharacterCreateView.as_view(),
        name='character-create'),
    url(r'^character/(?P<name>[^/]+)/?$',
        mgviews.CharacterView.as_view(),
        name='character'),
    url(r'^character/(?P<name>[^/]+)/edit/?$',
        mgviews.CharacterEditView.as_view(),
        name='character-edit'),
    url(r'^character/(?P<name>[^/]+)/delete/?$',
        mgviews.CharacterDeleteView.as_view(),
        name='character-delete'),
    url(r'^character/(?P<name>[^/]+)/jobs/?$',
        mgviews.JobsEditView.as_view(),
        name='character-jobs-edit'),
    url(r'^login_nonce/create/?$',
        mgviews.CreateLoginNonceView.as_view(),
        name='loginnonce-create'),
    url(r'^login_nonce/login/(?P<pk>[^/]+)/?$',
        mgviews.LoginByNonceView.as_view(),
        name='loginnonce-login'),
]
