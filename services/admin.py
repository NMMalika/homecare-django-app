from django.contrib import admin
from .models import ServiceCategory, Service


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1
    # ADDED 'slug' HERE 👇
    fields = ("name", "slug", "price", "icon_class", "is_active", "order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon_class", "order")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ServiceInline]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "get_price_nad",
        "is_active",
        "order",
    )
    list_filter = ("category", "is_active")
    search_fields = ("name", "short_description", "description")
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ("is_active", "order")

    @admin.display(description="Base Price (NAD)", ordering="price")
    def get_price_nad(self, obj):
        return obj.formatted_price