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
    """Create a simple dummy image file"""
    # Create a minimal valid JPEG file (1x1 pixel)
    jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfd\xd9'
    return ContentFile(jpeg_data, name='dummy.jpg')


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
