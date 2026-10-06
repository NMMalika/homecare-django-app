from django.shortcuts import redirect


class AdminRoleRedirectMiddleware:
    """
    Keep the Django administration restricted to SUPER_ADMIN.

    ADMIN users are sent to the custom Hands-On Health
    administration dashboard instead.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.path.startswith("/admin/"):

            if request.user.is_authenticated:

                if request.user.role == "ADMIN":
                    return redirect("staff:dashboard")

        return self.get_response(request)