from django.conf.urls import url

from jasonpi import views

urlpatterns = [
    url(r'^auth/s3$', views.s3_get_presigned_url),
    url(r'^auth/s3/signature$', views.s3_sign_policy_document),
    url(r'^auth/signin$', views.AuthSignInView.as_view()),
    url(r'^auth/signout$', views.signout),
    url(
        r'^auth/register$',
        views.AuthRegisterView.as_view({'post': 'create'}),
    ),
    url(r'^auth/provider$', views.AuthProviderView.as_view()),
]
