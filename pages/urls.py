from django.urls import path

from . import views


app_name = "pages"


urlpatterns = [

    path(
        "about/",
        views.about,
        name="about"
    ),

    path(
        "how-it-works/",
        views.how_it_works,
        name="how_it_works"
    ),

    path(
        "for-professionals/",
        views.professionals,
        name="professionals"
    ),

    path(
        "contact/",
        views.contact,
        name="contact"
    ),

]