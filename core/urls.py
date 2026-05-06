from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("properties/", views.property_list, name="property_list"),
    path("properties/<int:pk>/", views.property_detail, name="property_detail"),
    path("properties/<int:pk>/save/", views.toggle_saved_property, name="toggle_saved_property"),
    path("properties/<int:pk>/contact/", views.contact_seller, name="contact_seller"),
    path("seller/properties/<int:pk>/status/", views.update_property_status, name="update_property_status"),
    path("buyer/dashboard/", views.buyer_dashboard, name="buyer_dashboard"),
    path("saved-properties/", views.saved_properties, name="saved_properties"),
    path("inquiries/<int:pk>/chat/", views.inquiry_chat_room, name="inquiry_chat_room"),
    path("inquiries/<int:pk>/messages/", views.inquiry_chat_messages, name="inquiry_chat_messages"),
    path("api/inquiries/<int:pk>/mark-read/", views.api_mark_inquiry_read, name="api_mark_inquiry_read"),
    path("seller/dashboard/", views.seller_dashboard, name="seller_dashboard"),
    path("seller/properties/<int:pk>/edit/", views.edit_property, name="edit_property"),
    path("seller/properties/<int:pk>/delete/", views.delete_property, name="delete_property"),
    path("login/", views.login_view, name="login"),
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("verify-reset-otp/", views.verify_reset_otp_view, name="verify_reset_otp"),
    path("reset-password/", views.reset_password_view, name="reset_password"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("api/notifications/read/", views.api_mark_notifications_read, name="api_mark_notifications_read"),

    # ── Custom Admin Panel ────────────────────────────────────
    path("panel/", views.admin_dashboard, name="admin_dashboard"),
    path("panel/users/", views.admin_users, name="admin_users"),
    path("panel/users/create/", views.admin_user_create, name="admin_user_create"),
    path("panel/users/<int:pk>/edit/", views.admin_user_edit, name="admin_user_edit"),
    path("panel/users/<int:pk>/delete/", views.admin_user_delete, name="admin_user_delete"),
    path("panel/properties/", views.admin_properties, name="admin_properties"),
    path("panel/properties/create/", views.admin_property_create, name="admin_property_create"),
    path("panel/properties/pending/", views.admin_properties_pending, name="admin_properties_pending"),
    path("panel/properties/<int:pk>/", views.admin_property_detail, name="admin_property_detail"),
    path("panel/properties/<int:pk>/approve/", views.admin_property_approve, name="admin_property_approve"),
    path("panel/properties/<int:pk>/unapprove/", views.admin_property_unapprove, name="admin_property_unapprove"),
    path("panel/properties/<int:pk>/delete/", views.admin_property_delete, name="admin_property_delete"),
    path("panel/properties/<int:pk>/status/", views.admin_property_update_status, name="admin_property_update_status"),
    path("panel/inquiries/", views.admin_inquiries, name="admin_inquiries"),
    path("panel/inquiries/<int:pk>/", views.admin_inquiry_detail, name="admin_inquiry_detail"),
    path("panel/inquiries/<int:pk>/delete/", views.admin_inquiry_delete, name="admin_inquiry_delete"),
    path("panel/messages/", views.admin_messages, name="admin_messages"),
    path("panel/messages/<int:pk>/delete/", views.admin_message_delete, name="admin_message_delete"),
    path("panel/saved/", views.admin_saved_properties, name="admin_saved_properties"),
    path("panel/saved/<int:pk>/", views.admin_saved_property_detail, name="admin_saved_property_detail"),
    path("panel/saved/<int:pk>/delete/", views.admin_saved_property_delete, name="admin_saved_property_delete"),
]
