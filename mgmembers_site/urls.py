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
from django.conf import settings
from django.conf.urls import include
from django.conf.urls import url
from django.conf.urls.static import static
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
    url(r'^home/rema-augment-choice$',
        mgviews.RemaAugmentChoiceView.as_view(),
        name='rema-augment-choice'),
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
    url(r'^character/(?P<name>[^/]+)/omen-bosses-wishlist/?$',
        mgviews.OmenBossWishlistView.as_view(),
        name='character-omen-bosses-wishlist'),
    url(r'^character/(?P<name>[^/]+)/omen-bosses-clears/?$',
        mgviews.OmenBossesClearsView.as_view(),
        name='character-omen-bosses-clears'),
    url(r'^character/(?P<name>[^/]+)/woc-pops/?$',
        mgviews.WarderOfCouragePopsView.as_view(),
        name='character-woc-pops'),
    url(r'^character/(?P<name>[^/]+)/aeonics/?$',
        mgviews.AeonicsProgressView.as_view(),
        name='character-aeonics'),
    url(r'^character/(?P<name>[^/]+)/dynamis-gear/?$',
        mgviews.DynamisGearView.as_view(),
        name='character-dynamis-gear'),
    url(r'^character/(?P<name>[^/]+)/dynamis-wave3/?$',
        mgviews.DynamisWave3UpdateView.as_view(),
        name='character-dynamis-wave3'),
    url(r'^login_nonce/create/?$',
        mgviews.CreateLoginNonceView.as_view(),
        name='loginnonce-create'),
    url(r'^login_nonce/login/(?P<pk>[^/]+)/?$',
        mgviews.LoginByNonceView.as_view(),
        name='loginnonce-login'),
    url(r'^gear-choices-overview/?$',
        mgviews.GearChoicesOverview.as_view(),
        name='gear-choices-overview'),
    url(r'^gear-omen-scales/?$',
        mgviews.OmenScalesOverview.as_view(),
        name='gear-omen-scales'),
    url(r'^gear-dynamis-overview/?$',
        mgviews.DynamisGearOverview.as_view(),
        name='gear-dynamis-overview'),
    url(r'^gear-overview/loot.json$',
        mgviews.LootJsonView.as_view(),
        name='gear-overview-json'),
    url(r'^gear-rema-overview/?$',
        mgviews.RemaOverview.as_view(),
        name='gear-rema-overview'),
    url(r'^aeonics-overview/?$',
        mgviews.AeonicsOverview.as_view(),
        name='aeonics-overview'),
    url(r'^dyna-wave3-overview/?$',
        mgviews.DynamisWave3Overview.as_view(),
        name='dynamis-wave3-overview'),
    url(r'^about/?$',
        mgviews.LSInformationView.as_view(),
        name='about'),
    url(r'^dynamis_maps/?$',
        mgviews.TemplateView.as_view(template_name='mgmembers/dynamis_maps.html'),
        name='dynamis_maps'),
    url(r'^galleries/', include('photologue.urls', namespace='galleries')),
    url(r'^party_builder/',
        mgviews.PartyBuilder.as_view(),
        name="party-builder"),
]

# Serve media through development server
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
