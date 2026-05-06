import secrets
from datetime import timedelta

from django.contrib import messages as django_messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.urls import reverse
from django.utils.timezone import localtime
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import (
	AdminPanelPropertyForm,
	AdminPanelUserCreateForm,
	AdminPanelUserForm,
	OTPVerificationForm,
	PasswordResetNewPasswordForm,
	PasswordResetRequestForm,
	PropertyForm,
	RegisterForm,
)
from .models import ChatMessage, InquiryChat, PasswordResetOTP, Property, SavedProperty, User


PASSWORD_RESET_SESSION_USER = "password_reset_user_id"
PASSWORD_RESET_SESSION_OTP = "password_reset_otp_id"
PASSWORD_RESET_SESSION_VERIFIED = "password_reset_otp_verified"
OTP_VALIDITY_MINUTES = 10


def get_buyer_dashboard_context(user):
	inquiries = (
		InquiryChat.objects.filter(buyer=user)
		.select_related("property", "property__seller")
		.annotate(
			unread_count=Count(
				"messages",
				filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender_id=user.id),
			)
		)
	)
	return {
		"inquiries": inquiries,
	}


def get_seller_dashboard_context(user, form=None):
	if form is None:
		form = PropertyForm()

	properties = Property.objects.filter(seller=user).order_by("-created_at")
	inquiries = (
		InquiryChat.objects.filter(property__seller=user)
		.select_related("buyer", "property")
		.annotate(
			unread_count=Count(
				"messages",
				filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender_id=user.id),
			)
		)
	)
	return {
		"form": form,
		"properties": properties,
		"inquiries": inquiries,
	}


def redirect_by_role(user):
	if user.is_superuser or user.role == User.Role.ADMIN:
		return redirect("core:admin_dashboard")
	return redirect("core:dashboard")


def get_next_url(request):
	next_url = request.POST.get("next") or request.GET.get("next")
	if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
		return next_url
	return ""


def get_inquiry_for_user(request_user, pk):
	inquiry = get_object_or_404(
		InquiryChat.objects.select_related("buyer", "property", "property__seller"), pk=pk
	)
	is_buyer_owner = inquiry.buyer_id == request_user.id
	is_seller_owner = inquiry.property.seller_id == request_user.id
	return inquiry, is_buyer_owner, is_seller_owner


def serialize_chat_message(message, request_user):
	sender_role = "buyer" if message.sender_id == message.inquiry.buyer_id else "seller"
	return {
		"id": message.id,
		"message": message.message,
		"sender_id": message.sender_id,
		"sender_name": message.sender.username,
		"sender_role": sender_role,
		"is_self": message.sender_id == request_user.id,
		"created_at": localtime(message.created_at).isoformat(),
		"created_at_label": localtime(message.created_at).strftime("%b %d, %Y, %I:%M %p"),
	}


def mark_incoming_messages_read(inquiry, user):
	inquiry.messages.exclude(sender=user).filter(read_at__isnull=True).update(
		read_at=timezone.now()
	)


def home(request):
	featured_properties = (
		Property.objects.filter(is_verified=True)
		.select_related("seller")
		.order_by("-created_at")[:3]
	)
	return render(request, "core/home.html", {"featured_properties": featured_properties})


def login_view(request):
	if request.user.is_authenticated:
		return redirect_by_role(request.user)

	next_url = get_next_url(request)
	context = {"next_url": next_url, "selected_role": User.Role.BUYER}
	if request.GET.get("reset") == "1":
		context["success"] = "Password reset successful. Please log in with your new password."
	if request.method == "POST":
		username = request.POST.get("username", "").strip()
		password = request.POST.get("password", "")
		selected_role = request.POST.get("role", User.Role.BUYER)
		allowed_roles = {User.Role.BUYER, User.Role.SELLER, User.Role.ADMIN}
		if selected_role not in allowed_roles:
			selected_role = User.Role.BUYER

		context["selected_role"] = selected_role
		context["entered_username"] = username
		user = authenticate(request, username=username, password=password)
		if user is not None:
			actual_role = User.Role.ADMIN if user.is_superuser else user.role
			if selected_role != actual_role:
				context["error"] = "Selected role does not match this account."
				return render(request, "core/login.html", context)

			login(request, user)
			if next_url:
				return redirect(next_url)
			return redirect_by_role(user)
		context["error"] = "Invalid username or password."

	return render(request, "core/login.html", context)


def forgot_password_view(request):
	if request.user.is_authenticated:
		return redirect_by_role(request.user)

	form = PasswordResetRequestForm(request.POST or None)
	error = ""
	if request.method == "POST" and form.is_valid():
		email = form.cleaned_data["email"].strip()
		user = User.objects.filter(email__iexact=email).first()
		if user is None:
			error = "No account found with this email address."
		else:
			PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)
			otp = f"{secrets.randbelow(900000) + 100000}"
			expires_at = timezone.now() + timedelta(minutes=OTP_VALIDITY_MINUTES)
			otp_obj = PasswordResetOTP.objects.create(
				user=user,
				otp_hash=make_password(otp),
				expires_at=expires_at,
			)

			from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@urbanhunt.local")
			try:
				send_mail(
					subject="Urban Hunt password reset OTP",
					message=(
						f"Hello {user.username},\n\n"
						f"Use this OTP to reset your Urban Hunt password: {otp}\n"
						f"This OTP will expire in {OTP_VALIDITY_MINUTES} minutes.\n\n"
						"If you did not request this, please ignore this email."
					),
					from_email=from_email,
					recipient_list=[user.email],
					fail_silently=False,
				)
			except Exception:
				otp_obj.delete()
				error = "Failed to send OTP email. Please check email settings and try again."
			else:
				request.session[PASSWORD_RESET_SESSION_USER] = user.id
				request.session[PASSWORD_RESET_SESSION_OTP] = otp_obj.id
				request.session[PASSWORD_RESET_SESSION_VERIFIED] = False
				return redirect("core:verify_reset_otp")

	return render(
		request,
		"core/forgot_password.html",
		{
			"form": form,
			"error": error,
		},
	)


def verify_reset_otp_view(request):
	if request.user.is_authenticated:
		return redirect_by_role(request.user)

	user_id = request.session.get(PASSWORD_RESET_SESSION_USER)
	otp_id = request.session.get(PASSWORD_RESET_SESSION_OTP)
	if not user_id or not otp_id:
		return redirect("core:forgot_password")

	user = get_object_or_404(User, pk=user_id)
	otp_obj = PasswordResetOTP.objects.filter(pk=otp_id, user=user).first()
	if otp_obj is None or otp_obj.is_used or otp_obj.is_expired():
		request.session.pop(PASSWORD_RESET_SESSION_OTP, None)
		request.session[PASSWORD_RESET_SESSION_VERIFIED] = False
		return redirect("core:forgot_password")

	form = OTPVerificationForm(request.POST or None)
	error = ""
	if request.method == "POST" and form.is_valid():
		otp = form.cleaned_data["otp"]
		if check_password(otp, otp_obj.otp_hash):
			otp_obj.is_used = True
			otp_obj.save(update_fields=["is_used"])
			request.session[PASSWORD_RESET_SESSION_VERIFIED] = True
			return redirect("core:reset_password")
		error = "Invalid OTP. Please try again."

	return render(
		request,
		"core/verify_reset_otp.html",
		{
			"form": form,
			"masked_email": _mask_email(user.email),
			"error": error,
		},
	)


def reset_password_view(request):
	if request.user.is_authenticated:
		return redirect_by_role(request.user)

	user_id = request.session.get(PASSWORD_RESET_SESSION_USER)
	is_verified = request.session.get(PASSWORD_RESET_SESSION_VERIFIED, False)
	if not user_id or not is_verified:
		return redirect("core:forgot_password")

	user = get_object_or_404(User, pk=user_id)
	form = PasswordResetNewPasswordForm(user, request.POST or None)

	if request.method == "POST" and form.is_valid():
		form.save()
		request.session.pop(PASSWORD_RESET_SESSION_USER, None)
		request.session.pop(PASSWORD_RESET_SESSION_OTP, None)
		request.session.pop(PASSWORD_RESET_SESSION_VERIFIED, None)
		return redirect(f"{reverse('core:login')}?reset=1")

	return render(request, "core/reset_password.html", {"form": form})


def _mask_email(email):
	if "@" not in email:
		return email
	local, domain = email.split("@", 1)
	if len(local) <= 2:
		masked_local = local[0] + "*" * (len(local) - 1)
	else:
		masked_local = local[:2] + "*" * (len(local) - 2)
	return f"{masked_local}@{domain}"


def register_view(request):
	if request.user.is_authenticated:
		return redirect_by_role(request.user)

	if request.method == "POST":
		form = RegisterForm(request.POST)
		if form.is_valid():
			user = form.save()
			login(request, user)
			return redirect_by_role(user)
	else:
		form = RegisterForm()

	return render(request, "core/register.html", {"form": form})


@login_required
def logout_view(request):
	if request.method == "POST":
		logout(request)
		return redirect("core:home")
	return redirect_by_role(request.user)


@login_required
def dashboard(request):
	if request.user.is_superuser or request.user.role == User.Role.ADMIN:
		return redirect_by_role(request.user)

	context = {}
	if request.user.role == User.Role.BUYER:
		context.update(get_buyer_dashboard_context(request.user))
	elif request.user.role == User.Role.SELLER:
		if request.method == "POST":
			form = PropertyForm(request.POST, request.FILES)
			if form.is_valid():
				property_obj = form.save(commit=False)
				property_obj.seller = request.user
				property_obj.save()
				
				# Check if it's an AJAX request
				is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
				if is_ajax:
					return JsonResponse({
						'success': True,
						'message': 'Property created successfully!',
						'property': {
							'id': property_obj.id,
							'title': property_obj.title,
							'price': str(property_obj.price),
							'property_type': property_obj.get_property_type_display(),
							'status': property_obj.status,
							'status_display': property_obj.get_status_display(),
							'is_verified': property_obj.is_verified,
							'image_url': property_obj.image.url if property_obj.image else None,
						}
					})
				return redirect("core:dashboard")
			else:
				# For AJAX requests, return form errors
				is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
				if is_ajax:
					return JsonResponse({
						'success': False,
						'errors': form.errors
					}, status=400)
		else:
			form = PropertyForm()
		context.update(get_seller_dashboard_context(request.user, form=form))
	return render(request, "core/dashboard.html", context)


@login_required
def buyer_dashboard(request):
	if request.user.is_superuser or request.user.role != User.Role.BUYER:
		return redirect_by_role(request.user)
	return redirect("core:dashboard")


@login_required
def saved_properties(request):
	is_buyer = not request.user.is_superuser and request.user.role == User.Role.BUYER
	saved_items = SavedProperty.objects.none()

	if is_buyer:
		saved_items = SavedProperty.objects.filter(buyer=request.user).select_related(
			"property", "property__seller"
		)

	return render(request, "core/saved_properties.html", {
		"saved_items": saved_items,
		"can_save_properties": is_buyer,
	})


@login_required
def seller_dashboard(request):
	if request.user.is_superuser or request.user.role != User.Role.SELLER:
		return redirect_by_role(request.user)
	return redirect("core:dashboard")


@login_required
def edit_property(request, pk):
	if request.user.role != User.Role.SELLER:
		return redirect_by_role(request.user)

	property_obj = get_object_or_404(Property, pk=pk, seller=request.user)
	if request.method == "POST":
		form = PropertyForm(request.POST, request.FILES, instance=property_obj)
		if form.is_valid():
			updated = form.save(commit=False)
			updated.seller = request.user
			updated.save()
			
			is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
			if is_ajax:
				return JsonResponse({
					'success': True,
					'message': 'Property updated successfully.',
					'property_id': pk
				})
			
			return redirect("core:dashboard")
		else:
			is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
			if is_ajax:
				return JsonResponse({
					'success': False,
					'errors': form.errors
				}, status=400)
	else:
		form = PropertyForm(instance=property_obj)

	return render(
		request,
		"core/property_form.html",
		{"form": form, "property": property_obj, "is_edit": True},
	)


@login_required
def delete_property(request, pk):
	if request.user.role != User.Role.SELLER:
		return redirect_by_role(request.user)

	property_obj = get_object_or_404(Property, pk=pk, seller=request.user)
	if request.method == "POST":
		property_obj.delete()
		is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
		if is_ajax:
			return JsonResponse({'success': True, 'message': 'Property deleted successfully.'})
		return redirect("core:dashboard")

	return render(request, "core/property_form.html", {"property": property_obj, "is_delete": True})


@login_required
def update_property_status(request, pk):
	"""Allow sellers to update property status"""
	if request.method != "POST":
		return redirect("core:property_detail", pk=pk)
	if request.user.role != User.Role.SELLER:
		return redirect_by_role(request.user)

	property_obj = get_object_or_404(Property, pk=pk, seller=request.user)
	new_status = request.POST.get("status", "").strip()

	if new_status not in [choice[0] for choice in Property.PropertyStatus.choices]:
		new_data = {'success': False, 'message': 'Invalid status.'}
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			return JsonResponse(new_data, status=400)
		django_messages.error(request, "Invalid status.")
		return redirect("core:dashboard")

	property_obj.status = new_status
	property_obj.save(update_fields=["status"])
	
	is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
	if is_ajax:
		return JsonResponse({
			'success': True,
			'message': f"Property status updated to '{property_obj.get_status_display()}'.",
			'status': new_status,
			'status_display': property_obj.get_status_display(),
			'property_id': pk
		})
	
	django_messages.success(request, f"Property status updated to '{property_obj.get_status_display()}'.")
	return redirect("core:dashboard")


def property_list(request):
	properties = Property.objects.select_related("seller")
	show_unverified = False
	if request.user.is_authenticated:
		if request.user.is_superuser or request.user.role == User.Role.ADMIN:
			show_unverified = True
		elif request.user.role == User.Role.SELLER:
			show_unverified = True
			properties = properties.filter(Q(is_verified=True) | Q(seller=request.user))
		else:
			properties = properties.filter(is_verified=True)
	else:
		properties = properties.filter(is_verified=True)

	q = request.GET.get("q", "").strip()
	location = request.GET.get("location", "").strip()
	min_price = request.GET.get("min_price", "").strip()
	max_price = request.GET.get("max_price", "").strip()
	property_type = request.GET.get("property_type", "").strip()
	amenities = request.GET.get("amenities", "").strip()

	if q:
		properties = properties.filter(
			Q(title__icontains=q) | Q(location__icontains=q) | Q(description__icontains=q)
		)

	if location:
		properties = properties.filter(location__icontains=location)
	if min_price:
		properties = properties.filter(price__gte=min_price)
	if max_price:
		properties = properties.filter(price__lte=max_price)
	if property_type:
		properties = properties.filter(property_type=property_type)
	if amenities:
		for amenity in [item.strip() for item in amenities.split(",") if item.strip()]:
			properties = properties.filter(amenities__icontains=amenity)

	context = {
		"properties": properties.order_by("-created_at"),
		"filters": {
			"q": q,
			"location": location,
			"min_price": min_price,
			"max_price": max_price,
			"property_type": property_type,
			"amenities": amenities,
		},
		"property_type_choices": Property.PropertyType.choices,
		"show_unverified": show_unverified,
	}
	return render(request, "core/property_list.html", context)


def property_detail(request, pk):
	properties = Property.objects.select_related("seller")
	if request.user.is_authenticated:
		can_view_unverified = request.user.is_superuser or request.user.role == User.Role.ADMIN
		if not can_view_unverified:
			can_view_unverified = (
				request.user.role == User.Role.SELLER
				and properties.filter(pk=pk, seller=request.user).exists()
			)
		if can_view_unverified:
			property_obj = get_object_or_404(properties, pk=pk)
		else:
			property_obj = get_object_or_404(properties, pk=pk, is_verified=True)
	else:
		property_obj = get_object_or_404(properties, pk=pk, is_verified=True)

	is_saved = False
	if request.user.is_authenticated and request.user.role == User.Role.BUYER:
		is_saved = SavedProperty.objects.filter(buyer=request.user, property=property_obj).exists()

	return render(
		request,
		"core/property_detail.html",
		{"property": property_obj, "is_saved": is_saved},
	)


@login_required
def toggle_saved_property(request, pk):
	if request.method != "POST":
		return redirect("core:property_detail", pk=pk)
	if request.user.is_superuser or request.user.role != User.Role.BUYER:
		return redirect_by_role(request.user)

	property_obj = get_object_or_404(Property, pk=pk, is_verified=True)
	saved = SavedProperty.objects.filter(buyer=request.user, property=property_obj)
	is_saved = False
	
	if saved.exists():
		saved.delete()
		message = "Property removed from saved."
		button_text = "Save Property"
	else:
		SavedProperty.objects.create(buyer=request.user, property=property_obj)
		is_saved = True
		message = "Property saved successfully."
		button_text = "Remove from Saved"

	is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
	if is_ajax:
		return JsonResponse({
			'success': True,
			'message': message,
			'is_saved': is_saved,
			'button_text': button_text
		})

	next_url = get_next_url(request)
	if next_url:
		return redirect(next_url)
	return redirect("core:property_detail", pk=pk)


@login_required
def contact_seller(request, pk):
	if request.method != "POST":
		return redirect("core:property_detail", pk=pk)
	if request.user.is_superuser or request.user.role != User.Role.BUYER:
		return redirect_by_role(request.user)

	property_obj = get_object_or_404(Property, pk=pk, is_verified=True)
	is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
	
	# Check if property is available
	if property_obj.status != Property.PropertyStatus.AVAILABLE:
		status_msg = property_obj.get_status_display().lower()
		if property_obj.status == Property.PropertyStatus.SOLD:
			error_msg = f"This property has been sold and is no longer available for inquiry. Please explore other available properties."
		elif property_obj.status == Property.PropertyStatus.RENTED:
			error_msg = f"This property is currently on rent and not available for new inquiries."
		else:
			error_msg = f"This property is currently {status_msg}. You cannot contact the seller."
		
		if is_ajax:
			return JsonResponse({'success': False, 'message': error_msg}, status=400)
		
		django_messages.error(request, error_msg)
		return redirect("core:property_detail", pk=pk)
	
	message = request.POST.get("message", "").strip()
	if not message:
		message = "Hi, I am interested in this property. Please share more details."

	inquiry = InquiryChat.objects.filter(buyer=request.user, property=property_obj).first()
	if inquiry is None:
		inquiry = InquiryChat.objects.create(
			buyer=request.user,
			property=property_obj,
			message=message,
		)
	elif inquiry.message != message:
		inquiry.message = message
		inquiry.save(update_fields=["message"])

	ChatMessage.objects.create(inquiry=inquiry, sender=request.user, message=message)
	
	if is_ajax:
		return JsonResponse({
			'success': True,
			'message': 'Message sent to seller successfully.',
			'inquiry_id': inquiry.pk,
			'chat_url': reverse('core:inquiry_chat_room', kwargs={'pk': inquiry.pk})
		})
	
	return redirect("core:inquiry_chat_room", pk=inquiry.pk)


@login_required
def inquiry_chat_room(request, pk):
	inquiry, is_buyer_owner, is_seller_owner = get_inquiry_for_user(request.user, pk)
	if not (is_buyer_owner or is_seller_owner):
		return redirect_by_role(request.user)

	if request.method == "POST":
		# Prevent buyers from messaging on unavailable properties
		if is_buyer_owner and inquiry.property.status != Property.PropertyStatus.AVAILABLE:
			django_messages.error(request, f"This property is currently {inquiry.property.get_status_display().lower()} and is no longer available for messaging.")
			return redirect("core:inquiry_chat_room", pk=inquiry.pk)
		
		message = request.POST.get("message", "").strip()
		if message:
			ChatMessage.objects.create(inquiry=inquiry, sender=request.user, message=message)
		return redirect("core:inquiry_chat_room", pk=inquiry.pk)

	messages = inquiry.messages.select_related("sender")
	mark_incoming_messages_read(inquiry, request.user)
	return render(
		request,
		"core/inquiry_chat_room.html",
		{
			"inquiry": inquiry,
			"messages": messages,
			"is_buyer_owner": is_buyer_owner,
			"is_seller_owner": is_seller_owner,
			"latest_message_id": messages.last().id if messages.exists() else 0,
		},
	)


@login_required
def inquiry_chat_messages(request, pk):
	inquiry, is_buyer_owner, is_seller_owner = get_inquiry_for_user(request.user, pk)
	if not (is_buyer_owner or is_seller_owner):
		return JsonResponse({"error": "Forbidden"}, status=403)

	if request.method == "POST":
		message_text = request.POST.get("message", "").strip()
		if not message_text:
			return JsonResponse({"error": "Message is required."}, status=400)

		# Check if property is still available for buyer messages
		if is_buyer_owner and inquiry.property.status != Property.PropertyStatus.AVAILABLE:
			return JsonResponse({
				"error": f"This property is {inquiry.property.get_status_display().lower()}. Cannot send messages."
			}, status=400)

		message = ChatMessage.objects.create(
			inquiry=inquiry,
			sender=request.user,
			message=message_text,
		)
		message = (
			ChatMessage.objects.select_related("sender", "inquiry", "inquiry__buyer")
			.get(pk=message.pk)
		)
		return JsonResponse({"message": serialize_chat_message(message, request.user)}, status=201)

	since_id = request.GET.get("since_id", "").strip()
	message_qs = inquiry.messages.select_related("sender", "inquiry", "inquiry__buyer")
	if since_id.isdigit():
		message_qs = message_qs.filter(pk__gt=int(since_id))

	message_list = list(message_qs)
	unread_ids = [
		item.id
		for item in message_list
		if item.sender_id != request.user.id and item.read_at is None
	]
	if unread_ids:
		ChatMessage.objects.filter(pk__in=unread_ids).update(read_at=timezone.now())

	messages = [serialize_chat_message(item, request.user) for item in message_list]
	return JsonResponse({"messages": messages})


# ──────────────────────────────────────────────────────────────
# Admin Panel helpers
# ──────────────────────────────────────────────────────────────

def _require_admin(request):
	"""Return None if the user is an admin, otherwise return a redirect."""
	if not request.user.is_authenticated:
		return redirect(f"/login/?next={request.path}")
	if not (request.user.is_superuser or request.user.role == User.Role.ADMIN):
		return redirect("core:home")
	return None


def _paginate(qs, request, per_page=25):
	paginator = Paginator(qs, per_page)
	page_number = request.GET.get("page", 1)
	return paginator.get_page(page_number)


def _admin_stats():
	return {
		"total_users": User.objects.count(),
		"buyers": User.objects.filter(role=User.Role.BUYER).count(),
		"sellers": User.objects.filter(role=User.Role.SELLER).count(),
		"verified_properties": Property.objects.filter(is_verified=True).count(),
		"pending_properties": Property.objects.filter(is_verified=False).count(),
		"total_inquiries": InquiryChat.objects.count(),
		"total_messages": ChatMessage.objects.count(),
		"saved_properties": SavedProperty.objects.filter(buyer__role=User.Role.BUYER).count(),
	}


@login_required
def api_mark_notifications_read(request):
	if request.method == "POST":
		user = request.user
		if user.role == User.Role.BUYER:
			inquiries = InquiryChat.objects.filter(buyer=user)
		elif user.role == User.Role.SELLER:
			inquiries = InquiryChat.objects.filter(property__seller=user)
		else:
			return JsonResponse({"status": "ignored"})
		
		ChatMessage.objects.filter(
			inquiry__in=inquiries, read_at__isnull=True
		).exclude(sender=user).update(read_at=timezone.now())
		
		return JsonResponse({"status": "success"})
	return JsonResponse({"error": "Method not allowed"}, status=405)


@login_required
def api_mark_inquiry_read(request, pk):
	"""Mark messages in a specific inquiry as read and return updated notification count"""
	if request.method != "POST":
		return JsonResponse({"error": "Method not allowed"}, status=405)
	
	inquiry, is_buyer_owner, is_seller_owner = get_inquiry_for_user(request.user, pk)
	if not (is_buyer_owner or is_seller_owner):
		return JsonResponse({"error": "Unauthorized"}, status=403)
	
	# Mark messages as read
	mark_incoming_messages_read(inquiry, request.user)
	
	# Calculate updated notification count
	user = request.user
	if user.role == User.Role.BUYER:
		inquiries = InquiryChat.objects.filter(buyer=user)
	elif user.role == User.Role.SELLER:
		inquiries = InquiryChat.objects.filter(property__seller=user)
	else:
		inquiries = InquiryChat.objects.none()
	
	unread_count = ChatMessage.objects.filter(
		inquiry__in=inquiries, read_at__isnull=True
	).exclude(sender=user).count()
	
	return JsonResponse({
		"status": "success",
		"unread_count": unread_count
	})


# ──────────────────────────────────────────────────────────────
# Admin Dashboard
# ──────────────────────────────────────────────────────────────

@login_required
def admin_dashboard(request):
	guard = _require_admin(request)
	if guard:
		return guard

	stats = _admin_stats()
	recent_properties = Property.objects.select_related("seller").order_by("-created_at")[:6]
	recent_users = User.objects.filter(role__in=[User.Role.BUYER, User.Role.SELLER]).order_by("-date_joined")[:6]

	return render(request, "admin_panel/dashboard.html", {
		"stats": stats,
		"admin_stats": stats,
		"recent_properties": recent_properties,
		"recent_users": recent_users,
	})


# ──────────────────────────────────────────────────────────────
# Admin Users
# ──────────────────────────────────────────────────────────────

@login_required
def admin_users(request):
	guard = _require_admin(request)
	if guard:
		return guard

	qs = User.objects.filter(role__in=[User.Role.BUYER, User.Role.SELLER]).order_by("-date_joined")
	q = request.GET.get("q", "").strip()
	role = request.GET.get("role", "").strip()

	if q:
		qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))
	if role in {User.Role.BUYER, User.Role.SELLER}:
		qs = qs.filter(role=role)

	return render(request, "admin_panel/users.html", {
		"page_obj": _paginate(qs, request),
		"admin_stats": _admin_stats(),
	})


@login_required
def admin_user_edit(request, pk):
	guard = _require_admin(request)
	if guard:
		return guard

	user_obj = get_object_or_404(User, pk=pk, role__in=[User.Role.BUYER, User.Role.SELLER])
	if request.method == "POST":
		form = AdminPanelUserForm(request.POST, instance=user_obj)
		if form.is_valid():
			form.save()
			django_messages.success(request, f"Updated user '{user_obj.username}'.")
			return redirect("core:admin_users")
	else:
		form = AdminPanelUserForm(instance=user_obj)

	return render(request, "admin_panel/user_edit.html", {
		"form": form,
		"user_obj": user_obj,
		"admin_stats": _admin_stats(),
	})


@login_required
def admin_user_create(request):
	guard = _require_admin(request)
	if guard:
		return guard

	if request.method == "POST":
		form = AdminPanelUserCreateForm(request.POST)
		if form.is_valid():
			new_user = form.save()
			django_messages.success(request, f"Created user '{new_user.username}'.")
			return redirect("core:admin_users")
	else:
		form = AdminPanelUserCreateForm()

	return render(request, "admin_panel/user_create.html", {
		"form": form,
		"admin_stats": _admin_stats(),
	})


@login_required
def admin_user_delete(request, pk):
	guard = _require_admin(request)
	if guard:
		return guard
	if request.method == "POST":
		user_obj = get_object_or_404(User, pk=pk, role__in=[User.Role.BUYER, User.Role.SELLER])
		if user_obj.id == request.user.id:
			msg = "You cannot delete your own account."
			if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
				return JsonResponse({'success': False, 'message': msg}, status=400)
			django_messages.error(request, msg)
			return redirect("core:admin_users")
		username = user_obj.username
		user_obj.delete()
		msg = f"Deleted user '{username}'."
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			return JsonResponse({'success': True, 'message': msg})
		django_messages.success(request, msg)
	return redirect("core:admin_users")


# ──────────────────────────────────────────────────────────────
# Admin Properties
# ──────────────────────────────────────────────────────────────

@login_required
def admin_properties(request):
	guard = _require_admin(request)
	if guard:
		return guard

	qs = Property.objects.select_related("seller").order_by("-created_at")
	q = request.GET.get("q", "").strip()
	ptype = request.GET.get("type", "").strip()
	verified = request.GET.get("verified", "").strip()

	if q:
		qs = qs.filter(Q(title__icontains=q) | Q(location__icontains=q) | Q(seller__username__icontains=q))
	if ptype:
		qs = qs.filter(property_type=ptype)
	if verified == "1":
		qs = qs.filter(is_verified=True)
	elif verified == "0":
		qs = qs.filter(is_verified=False)

	return render(request, "admin_panel/properties.html", {
		"page_obj": _paginate(qs, request),
		"admin_stats": _admin_stats(),
	})


@login_required
def admin_property_create(request):
	guard = _require_admin(request)
	if guard:
		return guard

	if request.method == "POST":
		form = AdminPanelPropertyForm(request.POST, request.FILES)
		if form.is_valid():
			prop = form.save()
			django_messages.success(request, f"Created property '{prop.title}'.")
			return redirect("core:admin_properties")
	else:
		form = AdminPanelPropertyForm()

	return render(request, "admin_panel/property_create.html", {
		"form": form,
		"admin_stats": _admin_stats(),
	})


@login_required
def admin_property_detail(request, pk):
	guard = _require_admin(request)
	if guard:
		return guard

	property_obj = get_object_or_404(Property.objects.select_related("seller"), pk=pk)

	return render(request, "admin_panel/property_detail.html", {
		"property": property_obj,
		"admin_stats": _admin_stats(),
	})


@login_required
def admin_properties_pending(request):
	guard = _require_admin(request)
	if guard:
		return guard

	qs = Property.objects.filter(is_verified=False).select_related("seller").order_by("-created_at")
	return render(request, "admin_panel/properties_pending.html", {
		"page_obj": _paginate(qs, request),
		"admin_stats": _admin_stats(),
	})


@login_required
def admin_property_approve(request, pk):
	guard = _require_admin(request)
	if guard:
		return guard
	if request.method == "POST":
		prop = get_object_or_404(Property, pk=pk)
		prop.is_verified = True
		prop.save(update_fields=["is_verified"])
		msg = f"'{prop.title}' has been approved."
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			return JsonResponse({'success': True, 'message': msg})
		django_messages.success(request, msg)
	return redirect(request.META.get("HTTP_REFERER", "core:admin_properties"))


@login_required
def admin_property_unapprove(request, pk):
	guard = _require_admin(request)
	if guard:
		return guard
	if request.method == "POST":
		prop = get_object_or_404(Property, pk=pk)
		prop.is_verified = False
		prop.save(update_fields=["is_verified"])
		msg = f"Verification revoked for '{prop.title}'."
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			return JsonResponse({'success': True, 'message': msg})
		django_messages.success(request, msg)
	return redirect(request.META.get("HTTP_REFERER", "core:admin_properties"))


@login_required
def admin_property_delete(request, pk):
	guard = _require_admin(request)
	if guard:
		return guard
	if request.method == "POST":
		prop = get_object_or_404(Property, pk=pk)
		title = prop.title
		prop.delete()
		msg = f"Deleted property '{title}'."
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			return JsonResponse({'success': True, 'message': msg})
		django_messages.success(request, msg)
	return redirect("core:admin_properties")


@login_required
def admin_property_update_status(request, pk):
	"""Allow admins to update property status"""
	guard = _require_admin(request)
	if guard:
		return guard
	
	if request.method == "POST":
		prop = get_object_or_404(Property, pk=pk)
		new_status = request.POST.get("status", "").strip()

		if new_status not in [choice[0] for choice in Property.PropertyStatus.choices]:
			msg = "Invalid status."
			if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
				return JsonResponse({'success': False, 'message': msg}, status=400)
			django_messages.error(request, msg)
			return redirect(request.META.get("HTTP_REFERER", f"core:admin_property_detail pk={pk}"))

		prop.status = new_status
		prop.save(update_fields=["status"])
		msg = f"Property status updated to '{prop.get_status_display()}'."
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			return JsonResponse({'success': True, 'message': msg})
		django_messages.success(request, msg)
	
	return redirect(request.META.get("HTTP_REFERER", "core:admin_properties"))


# ──────────────────────────────────────────────────────────────
# Admin Inquiries
# ──────────────────────────────────────────────────────────────

@login_required
def admin_inquiries(request):
	guard = _require_admin(request)
	if guard:
		return guard

	qs = InquiryChat.objects.select_related("buyer", "property", "property__seller").annotate(
		msg_count=Count("messages")
	).order_by("-created_at")

	q = request.GET.get("q", "").strip()
	if q:
		qs = qs.filter(
			Q(buyer__username__icontains=q) |
			Q(property__title__icontains=q) |
			Q(message__icontains=q)
		)

	return render(request, "admin_panel/inquiries.html", {
		"page_obj": _paginate(qs, request),
		"admin_stats": _admin_stats(),
	})


@login_required
def admin_inquiry_detail(request, pk):
	guard = _require_admin(request)
	if guard:
		return guard

	inquiry = get_object_or_404(
		InquiryChat.objects.select_related("buyer", "property", "property__seller"),
		pk=pk,
	)
	messages_qs = inquiry.messages.select_related("sender").order_by("created_at")

	return render(request, "admin_panel/inquiry_detail.html", {
		"inquiry": inquiry,
		"messages": messages_qs,
		"admin_stats": _admin_stats(),
	})


@login_required
def admin_inquiry_delete(request, pk):
	guard = _require_admin(request)
	if guard:
		return guard
	if request.method == "POST":
		inquiry = get_object_or_404(InquiryChat, pk=pk)
		inquiry.delete()
		msg = "Deleted inquiry thread."
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			return JsonResponse({'success': True, 'message': msg})
		django_messages.success(request, msg)
	return redirect("core:admin_inquiries")


# ──────────────────────────────────────────────────────────────
# Admin Chat Messages
# ──────────────────────────────────────────────────────────────

@login_required
def admin_messages(request):
	guard = _require_admin(request)
	if guard:
		return guard

	qs = ChatMessage.objects.select_related(
		"sender", "inquiry", "inquiry__property"
	).order_by("-created_at")

	q = request.GET.get("q", "").strip()
	read_filter = request.GET.get("read", "").strip()

	if q:
		qs = qs.filter(Q(sender__username__icontains=q) | Q(message__icontains=q))
	if read_filter == "unread":
		qs = qs.filter(read_at__isnull=True)
	elif read_filter == "read":
		qs = qs.filter(read_at__isnull=False)

	return render(request, "admin_panel/messages.html", {
		"page_obj": _paginate(qs, request),
		"admin_stats": _admin_stats(),
	})


@login_required
def admin_message_delete(request, pk):
	guard = _require_admin(request)
	if guard:
		return guard
	if request.method == "POST":
		msg = get_object_or_404(ChatMessage, pk=pk)
		msg.delete()
		message = "Deleted chat message."
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			return JsonResponse({'success': True, 'message': message})
		django_messages.success(request, message)
	return redirect("core:admin_messages")


# ──────────────────────────────────────────────────────────────
# Admin Saved Properties
# ──────────────────────────────────────────────────────────────

@login_required
def admin_saved_properties(request):
	guard = _require_admin(request)
	if guard:
		return guard

	qs = SavedProperty.objects.select_related(
		"buyer", "property", "property__seller"
	).filter(
		buyer__role=User.Role.BUYER
	).order_by("-created_at")

	q = request.GET.get("q", "").strip()
	if q:
		qs = qs.filter(
			Q(buyer__username__icontains=q) |
			Q(property__title__icontains=q)
		)

	return render(request, "admin_panel/saved_properties.html", {
		"page_obj": _paginate(qs, request),
		"admin_stats": _admin_stats(),
	})


@login_required
def admin_saved_property_detail(request, pk):
	guard = _require_admin(request)
	if guard:
		return guard

	saved_item = get_object_or_404(
		SavedProperty.objects.select_related("buyer", "property", "property__seller"),
		buyer__role=User.Role.BUYER,
		pk=pk,
	)

	return render(request, "admin_panel/saved_property_detail.html", {
		"saved_item": saved_item,
		"admin_stats": _admin_stats(),
	})


@login_required
def admin_saved_property_delete(request, pk):
	guard = _require_admin(request)
	if guard:
		return guard
	if request.method == "POST":
		saved = get_object_or_404(SavedProperty, pk=pk)
		saved.delete()
		msg = "Deleted saved property entry."
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			return JsonResponse({'success': True, 'message': msg})
		django_messages.success(request, msg)
	return redirect("core:admin_saved_properties")
