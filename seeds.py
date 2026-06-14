"""
Database seeding script for Urban Hunt project.
Creates admin user and realistic fake data for testing.

Usage: python manage.py shell < seeds.py
"""

from core.models import User, Property, InquiryChat, ChatMessage, SavedProperty
from django.utils import timezone
from datetime import timedelta
from django.core.files.base import ContentFile


def create_dummy_image():
    """Create a visible test image using PIL/Pillow"""
    from PIL import Image, ImageDraw
    import io
    
    # Create a 400x300 pixel image with a nice gradient and text
    img = Image.new('RGB', (400, 300), color=(70, 130, 180))  # Steel blue background
    draw = ImageDraw.Draw(img)
    
    # Draw a gradient effect with rectangles
    for i in range(300):
        color_value = int(70 + (i / 300) * 60)
        draw.line([(0, i), (400, i)], fill=(color_value, 130, 180))
    
    # Add text
    text = "Urban Hunt\nProperty Image"
    draw.text((100, 120), text, fill=(255, 255, 255))
    
    # Save to bytes
    img_io = io.BytesIO()
    img.save(img_io, format='JPEG', quality=85)
    img_io.seek(0)
    
    return ContentFile(img_io.read(), name='property.jpg')


def create_dummy_pdf():
    """Create a simple dummy PDF file"""
    pdf_data = b'%PDF-1.4\n%\xE2\xE3\xCF\xD3\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Property Document) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000214 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n308\n%%EOF'
    return ContentFile(pdf_data, name='dummy.pdf')


def create_admin():
    """Step A: Create admin user with exact credentials"""
    admin_user = User.objects.create_superuser(
        username="admin",
        email="admin@gmail.com",
        password="admin",
        role=User.Role.ADMIN,
    )
    print(f"✓ Created admin user: {admin_user.username}")
    return admin_user


def create_test_data():
    """Step B: Generate 5 realistic fake data examples for database entities"""
    
    # Create 2 seller users
    seller1 = User.objects.create_user(
        username="seller_john",
        email="john.seller@gmail.com",
        password="seller123",
        role=User.Role.SELLER,
        mobile_no="+919876543210",
        first_name="John",
        last_name="Smith",
    )
    print(f"✓ Created seller: {seller1.username}")
    
    seller2 = User.objects.create_user(
        username="seller_priya",
        email="priya.seller@gmail.com",
        password="seller123",
        role=User.Role.SELLER,
        mobile_no="+918765432109",
        first_name="Priya",
        last_name="Sharma",
    )
    print(f"✓ Created seller: {seller2.username}")
    
    # Create 3 buyer users
    buyer1 = User.objects.create_user(
        username="buyer_amit",
        email="amit.buyer@gmail.com",
        password="buyer123",
        role=User.Role.BUYER,
        mobile_no="+917654321098",
        first_name="Amit",
        last_name="Kumar",
    )
    print(f"✓ Created buyer: {buyer1.username}")
    
    buyer2 = User.objects.create_user(
        username="buyer_neha",
        email="neha.buyer@gmail.com",
        password="buyer123",
        role=User.Role.BUYER,
        mobile_no="+916543210987",
        first_name="Neha",
        last_name="Patel",
    )
    print(f"✓ Created buyer: {buyer2.username}")
    
    buyer3 = User.objects.create_user(
        username="buyer_rajesh",
        email="rajesh.buyer@gmail.com",
        password="buyer123",
        role=User.Role.BUYER,
        mobile_no="+915432109876",
        first_name="Rajesh",
        last_name="Verma",
    )
    print(f"✓ Created buyer: {buyer3.username}")
    
    # Create 5 properties for sale/rent
    properties = []
    
    property1 = Property.objects.create(
        title="Modern 2BHK Apartment in Downtown",
        description="Spacious 2-bedroom apartment with modern amenities, close to metro station, well-maintained building.",
        price="45 lakh",
        location="Downtown City Center",
        property_type=Property.PropertyType.SELL,
        amenities="WiFi, Parking, Gym, Swimming Pool, Security 24/7",
        image=create_dummy_image(),
        documents=create_dummy_pdf(),
        seller=seller1,
        is_verified=True,
        status=Property.PropertyStatus.AVAILABLE,
    )
    properties.append(property1)
    print(f"✓ Created property: {property1.title}")
    
    property2 = Property.objects.create(
        title="Cozy 1BHK for Rent Near Business District",
        description="Well-furnished 1-bedroom apartment ideal for young professionals, recently renovated.",
        price="25,000/month",
        location="Business District",
        property_type=Property.PropertyType.RENT,
        amenities="WiFi, Furnished, AC, Water Supply",
        image=create_dummy_image(),
        seller=seller1,
        is_verified=True,
        status=Property.PropertyStatus.AVAILABLE,
    )
    properties.append(property2)
    print(f"✓ Created property: {property2.title}")
    
    property3 = Property.objects.create(
        title="Luxurious 3BHK Villa with Garden",
        description="Premium 3-bedroom villa with private garden, swimming pool, and landscaped lawn.",
        price="2.5 cr",
        location="Upscale Residential Area",
        property_type=Property.PropertyType.SELL,
        amenities="Swimming Pool, Garden, Security, Parking, Gym",
        image=create_dummy_image(),
        documents=create_dummy_pdf(),
        seller=seller2,
        is_verified=True,
        status=Property.PropertyStatus.AVAILABLE,
    )
    properties.append(property3)
    print(f"✓ Created property: {property3.title}")
    
    property4 = Property.objects.create(
        title="Studio Apartment in Tech Park",
        description="Modern studio apartment in tech park area, perfect for bachelor or couple.",
        price="18,500/month",
        location="Tech Park Avenue",
        property_type=Property.PropertyType.RENT,
        amenities="WiFi, Furnished, Gym, Security",
        image=create_dummy_image(),
        seller=seller2,
        is_verified=True,
        status=Property.PropertyStatus.AVAILABLE,
    )
    properties.append(property4)
    print(f"✓ Created property: {property4.title}")
    
    property5 = Property.objects.create(
        title="Spacious Penthouse with City View",
        description="Exquisite penthouse with panoramic city views, modern kitchen, and home theater.",
        price="3.8 cr",
        location="High-Rise Central",
        property_type=Property.PropertyType.SELL,
        amenities="Concierge, Wine Cellar, Home Theater, Smart Home",
        image=create_dummy_image(),
        documents=create_dummy_pdf(),
        seller=seller1,
        is_verified=True,
        status=Property.PropertyStatus.AVAILABLE,
    )
    properties.append(property5)
    print(f"✓ Created property: {property5.title}")
    
    # Create inquiry chats
    inquiry1 = InquiryChat.objects.create(
        buyer=buyer1,
        property=property1,
        message="Is this apartment still available? Can we schedule a visit?",
    )
    print(f"✓ Created inquiry from {buyer1.username} for {property1.title}")
    
    inquiry2 = InquiryChat.objects.create(
        buyer=buyer2,
        property=property3,
        message="What are the payment terms for this villa?",
    )
    print(f"✓ Created inquiry from {buyer2.username} for {property3.title}")
    
    inquiry3 = InquiryChat.objects.create(
        buyer=buyer3,
        property=property2,
        message="When can I move in? Is the lease flexible?",
    )
    print(f"✓ Created inquiry from {buyer3.username} for {property2.title}")
    
    # Create chat messages
    msg1 = ChatMessage.objects.create(
        inquiry=inquiry1,
        sender=buyer1,
        message="Is this apartment still available? Can we schedule a visit?",
    )
    print(f"✓ Created chat message from {buyer1.username}")
    
    msg2 = ChatMessage.objects.create(
        inquiry=inquiry1,
        sender=seller1,
        message="Yes, it's available! You can visit any day between 10 AM to 6 PM. Please confirm your preferred time.",
        read_at=timezone.now(),
    )
    print(f"✓ Created chat message from {seller1.username}")
    
    msg3 = ChatMessage.objects.create(
        inquiry=inquiry2,
        sender=buyer2,
        message="What are the payment terms for this villa?",
    )
    print(f"✓ Created chat message from {buyer2.username}")
    
    msg4 = ChatMessage.objects.create(
        inquiry=inquiry3,
        sender=buyer3,
        message="When can I move in? Is the lease flexible?",
    )
    print(f"✓ Created chat message from {buyer3.username}")
    
    msg5 = ChatMessage.objects.create(
        inquiry=inquiry3,
        sender=seller2,
        message="You can move in within 30 days. Lease terms are flexible - we can discuss based on your requirements.",
        read_at=timezone.now(),
    )
    print(f"✓ Created chat message from {seller2.username}")
    
    # Create saved properties
    saved1 = SavedProperty.objects.create(
        buyer=buyer1,
        property=property3,
    )
    print(f"✓ {buyer1.username} saved {property3.title}")
    
    saved2 = SavedProperty.objects.create(
        buyer=buyer1,
        property=property5,
    )
    print(f"✓ {buyer1.username} saved {property5.title}")
    
    saved3 = SavedProperty.objects.create(
        buyer=buyer2,
        property=property1,
    )
    print(f"✓ {buyer2.username} saved {property1.title}")
    
    saved4 = SavedProperty.objects.create(
        buyer=buyer3,
        property=property4,
    )
    print(f"✓ {buyer3.username} saved {property4.title}")
    
    saved5 = SavedProperty.objects.create(
        buyer=buyer3,
        property=property2,
    )
    print(f"✓ {buyer3.username} saved {property2.title}")
    
    print("\n✅ Database seeding completed successfully!")
    print(f"\nAdmin Credentials:")
    print(f"  Username: admin")
    print(f"  Email: admin@gmail.com")
    print(f"  Password: admin")
    print(f"\nTest Users Created:")
    print(f"  Sellers: {seller1.username}, {seller2.username}")
    print(f"  Buyers: {buyer1.username}, {buyer2.username}, {buyer3.username}")
    print(f"\nTotal Data Created:")
    print(f"  - 1 Admin User")
    print(f"  - 2 Sellers + 3 Buyers")
    print(f"  - 5 Properties (3 for sale, 2 for rent)")
    print(f"  - 3 Inquiry Chats with 5 Messages")
    print(f"  - 5 Saved Properties")


print("Starting database seeding...\n")
create_admin()
create_test_data()
