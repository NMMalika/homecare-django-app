from django.shortcuts import render


def about(request):

    return render(
        request,
        "pages/about.html"
    )


def how_it_works(request):

    return render(
        request,
        "pages/how_it_works.html"
    )


def professionals(request):

    return render(
        request,
        "pages/professionals.html"
    )


def contact(request):

    return render(
        request,
        "pages/contact.html"
    )