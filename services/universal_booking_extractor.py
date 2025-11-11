"""
Universal Booking Data Extractor - ดึงข้อมูลจาก booking จริงทุก fields ทุก booking
พร้อม Smart Price Calculation แบบ real-time
"""

import logging
from decimal import Decimal
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class UniversalBookingExtractor:
    """ดึงข้อมูลจาก booking database จริงทุก fields สำหรับ Quote PDF"""
    
    @staticmethod
    def get_fresh_booking_data(booking_id):
        """ดึงข้อมูล booking ใหม่จาก database พร้อมทุก relationships แบบ real-time"""
        try:
            from models.booking import Booking
            from extensions import db
            from flask import current_app
            
            # Ensure we're in application context
            if not current_app:
                logger.error("❌ No Flask application context available")
                return None
            
            # ✅ Force expire all sessions and get completely fresh data
            db.session.expire_all()
            
            # ✅ Directly query the database with all relationships
            booking = db.session.query(Booking).options(
                db.joinedload(Booking.customer),
                db.joinedload(Booking.quotes) if hasattr(Booking, 'quotes') else db.noload(),
            ).filter(Booking.id == booking_id).first()
                
            if booking:
                # ✅ Force refresh individual object to ensure latest data
                db.session.refresh(booking)
                
                # ✅ Also refresh customer if exists
                if booking.customer:
                    db.session.refresh(booking.customer)
                
                logger.info(f'✅ Successfully fetched FRESH booking data for ID {booking_id}')
                logger.info(f'📋 Booking reference: {booking.booking_reference}')
                logger.info(f'📅 Updated at: {booking.updated_at if hasattr(booking, "updated_at") else "N/A"}')
                logger.info(f'👤 Customer: {booking.customer.name if booking.customer else "No customer"}')
                logger.info(f'💰 Total amount: {booking.total_amount}')
                logger.info(f'📊 Status: {booking.status}')
                
                return booking
            else:
                logger.warning(f'❌ Booking {booking_id} not found')
                return None
                
        except Exception as e:
            logger.error(f'❌ Error fetching fresh booking {booking_id}: {e}')
            # Try rollback and retry once
            try:
                db.session.rollback()
                booking = db.session.query(Booking).filter(Booking.id == booking_id).first()
                if booking:
                    db.session.refresh(booking)
                logger.info(f'✅ Retry successful for booking {booking_id}')
                return booking
            except Exception as retry_error:
                logger.error(f'❌ Retry also failed: {retry_error}')
                return None
    
    @staticmethod
    def extract_all_booking_fields(booking):
        """ดึงทุก fields จาก booking สำหรับ template แบบครบถ้วน Real-time"""
        extracted_data = {}
        
        try:
            # Force refresh booking data
            from extensions import db
            db.session.refresh(booking)
            
            # ดึงทุก attributes ของ booking
            booking_attrs = [attr for attr in dir(booking) if not attr.startswith('_') and not callable(getattr(booking, attr))]
            
            for attr in booking_attrs:
                try:
                    value = getattr(booking, attr)
                    
                    # แปลง datetime objects
                    if hasattr(value, 'strftime'):
                        extracted_data[attr] = value
                        extracted_data[f'{attr}_formatted'] = value.strftime('%d/%m/%Y')
                        extracted_data[f'{attr}_iso'] = value.isoformat()
                    
                    # แปลง Decimal objects
                    elif isinstance(value, Decimal):
                        extracted_data[attr] = float(value)
                        extracted_data[f'{attr}_formatted'] = f"{float(value):,.2f}"
                    
                    # แปลง Boolean
                    elif isinstance(value, bool):
                        extracted_data[attr] = value
                        extracted_data[f'{attr}_text'] = 'Yes' if value else 'No'
                    
                    # String และ Number values
                    elif value is not None:
                        extracted_data[attr] = value
                        
                        # สำหรับ text fields ที่มี line breaks
                        if isinstance(value, str) and '\n' in value:
                            extracted_data[f'{attr}_html'] = value.replace('\n', '<br>')
                            extracted_data[f'{attr}_lines'] = value.split('\n')
                
                except Exception as e:
                    logger.warning(f'Could not extract field {attr}: {e}')
                    continue
            
            # 🔥 เพิ่มการดึงข้อมูลสำคัญเพิ่มเติม
            
            # Products & Calculation ข้อมูล
            if hasattr(booking, 'products') and booking.products:
                extracted_data['products_data'] = booking.products
                logger.info(f'Products data: {booking.products}')
            
            # Service Details / Itinerary
            if hasattr(booking, 'service_details') and booking.service_details:
                extracted_data['service_details_current'] = booking.service_details
                logger.info(f'Service details: {booking.service_details[:100]}...')
            
            if hasattr(booking, 'itinerary') and booking.itinerary:
                extracted_data['itinerary_current'] = booking.itinerary
                logger.info(f'Itinerary: {booking.itinerary[:100]}...')
                
            # Name List / Rooming List
            if hasattr(booking, 'guest_list') and booking.guest_list:
                extracted_data['guest_list_current'] = booking.guest_list
                logger.info(f'Guest list: {booking.guest_list[:100]}...')
                
            if hasattr(booking, 'rooming_list') and booking.rooming_list:
                extracted_data['rooming_list_current'] = booking.rooming_list
                logger.info(f'Rooming list: {booking.rooming_list[:100]}...')
                
            # Flight Information
            for flight_field in ['flight_info', 'flight_details', 'flight_info_text']:
                if hasattr(booking, flight_field):
                    flight_value = getattr(booking, flight_field)
                    if flight_value:
                        extracted_data[f'{flight_field}_current'] = flight_value
                        logger.info(f'{flight_field}: {str(flight_value)[:100]}...')
            
            logger.info(f'✅ Extracted {len(extracted_data)} fields from booking {booking.id} (Real-time)')
            return extracted_data
            
        except Exception as e:
            logger.error(f'Error extracting booking fields: {e}')
            return {}
    
    @staticmethod
    def extract_universal_products(booking):
        """ดึงข้อมูล products แบบ universal สำหรับ booking ทุกประเภท - Smart Price Calculation"""
        products = []
        
        try:
            # วิธี 1: จาก booking.get_products() method ถ้ามี
            if hasattr(booking, 'get_products') and callable(getattr(booking, 'get_products')):
                booking_products = booking.get_products()
                if booking_products and len(booking_products) > 0:
                    return UniversalBookingExtractor._format_booking_products(booking_products)
            
            # วิธี 2: จาก line_items relationship ถ้ามี
            if hasattr(booking, 'line_items') and booking.line_items:
                return UniversalBookingExtractor._extract_from_line_items(booking.line_items)
            
            # วิธี 3: จาก booking_items relationship ถ้ามี
            if hasattr(booking, 'booking_items') and booking.booking_items:
                return UniversalBookingExtractor._extract_from_booking_items(booking.booking_items)
            
            # วิธี 4: จาก product_breakdown JSON field
            if hasattr(booking, 'product_breakdown') and booking.product_breakdown:
                return UniversalBookingExtractor._extract_from_product_breakdown(booking.product_breakdown)
            
            # วิธี 5: จาก passenger counts (traditional method)
            products = UniversalBookingExtractor._extract_from_passenger_counts(booking)
            
            # เพิ่ม discounts และ additional charges
            UniversalBookingExtractor._add_discounts_and_charges(booking, products)
            
            return products
            
        except Exception as e:
            logger.error(f'Error extracting products from booking {booking.id}: {e}')
            return []
    
    @staticmethod
    def _format_booking_products(booking_products):
        """Format products จาก booking.get_products() method"""
        formatted_products = []
        
        for i, product in enumerate(booking_products, 1):
            try:
                # ดึงข้อมูลจาก product dict
                name = product.get('name', f'Product {i}')
                quantity = int(product.get('quantity', 1))
                price = float(product.get('price', 0))
                amount = float(product.get('amount', quantity * price))
                
                formatted_products.append({
                    'no': i,
                    'name': name,
                    'quantity': quantity,
                    'price': f"{price:,.2f}",
                    'amount': f"{amount:,.2f}",
                    'is_negative': amount < 0,
                    'category': product.get('category', 'product'),
                    'raw_price': price,
                    'raw_amount': amount
                })
            except (ValueError, TypeError) as e:
                logger.warning(f'Error formatting product {i}: {e}')
                continue
                
        return formatted_products
    
    @staticmethod
    def _extract_from_line_items(line_items):
        """ดึงจาก line_items table"""
        products = []
        for idx, item in enumerate(line_items, 1):
            try:
                quantity = getattr(item, 'quantity', 1) or 1
                unit_price = float(getattr(item, 'unit_price', 0) or 0)
                total_price = float(getattr(item, 'total_price', 0) or getattr(item, 'line_total', 0) or (quantity * unit_price))
                
                products.append({
                    'no': idx,
                    'name': getattr(item, 'product_name', None) or getattr(item, 'description', None) or getattr(item, 'item_name', None) or f'Item {idx}',
                    'quantity': quantity,
                    'price': f"{unit_price:,.2f}",
                    'amount': f"{total_price:,.2f}",
                    'is_negative': total_price < 0,
                    'category': getattr(item, 'category', 'product'),
                    'raw_price': unit_price,
                    'raw_amount': total_price
                })
            except (ValueError, TypeError) as e:
                logger.warning(f'Error processing line item {idx}: {e}')
                continue
                
        return products
    
    @staticmethod
    def _extract_from_booking_items(booking_items):
        """ดึงจาก booking_items table"""
        products = []
        for idx, item in enumerate(booking_items, 1):
            try:
                quantity = getattr(item, 'qty', None) or getattr(item, 'quantity', 1) or 1
                price = float(getattr(item, 'price', 0) or getattr(item, 'unit_price', 0) or 0)
                total = float(getattr(item, 'total', 0) or getattr(item, 'amount', 0) or (quantity * price))
                
                products.append({
                    'no': idx,
                    'name': getattr(item, 'name', None) or getattr(item, 'title', None) or getattr(item, 'service_name', None) or f'Service {idx}',
                    'quantity': quantity,
                    'price': f"{price:,.2f}",
                    'amount': f"{total:,.2f}",
                    'is_negative': total < 0,
                    'category': getattr(item, 'type', 'service'),
                    'raw_price': price,
                    'raw_amount': total
                })
            except (ValueError, TypeError) as e:
                logger.warning(f'Error processing booking item {idx}: {e}')
                continue
                
        return products
    
    @staticmethod
    def _extract_from_product_breakdown(product_breakdown):
        """ดึงจาก product_breakdown JSON field"""
        products = []
        try:
            if isinstance(product_breakdown, str):
                breakdown = json.loads(product_breakdown)
            else:
                breakdown = product_breakdown
                
            for idx, (key, item) in enumerate(breakdown.items(), 1):
                if isinstance(item, dict):
                    quantity = item.get('quantity', 1)
                    price = float(item.get('price', 0))
                    amount = float(item.get('amount', quantity * price))
                    
                    products.append({
                        'no': idx,
                        'name': item.get('name', key),
                        'quantity': quantity,
                        'price': f"{price:,.2f}",
                        'amount': f"{amount:,.2f}",
                        'is_negative': amount < 0,
                        'category': item.get('category', 'product'),
                        'raw_price': price,
                        'raw_amount': amount
                    })
        except (json.JSONDecodeError, AttributeError) as e:
            logger.warning(f'Could not parse product_breakdown: {e}')
            
        return products
    
    @staticmethod
    def _extract_from_passenger_counts(booking):
        """ดึงจาก adults, children, infants counts (วิธีดั้งเดิม)"""
        products = []
        row_number = 1
        
        # Adults
        adults = getattr(booking, 'adults', 0) or 0
        if adults > 0:
            adt_price = UniversalBookingExtractor._get_dynamic_price(booking, 'adult')
            amount = adults * adt_price
            products.append({
                'no': row_number,
                'name': 'ADT',
                'quantity': adults,
                'price': f"{adt_price:,.2f}",
                'amount': f"{amount:,.2f}",
                'category': 'passenger',
                'raw_price': adt_price,
                'raw_amount': amount
            })
            row_number += 1
        
        # Children
        children = getattr(booking, 'children', 0) or 0
        if children > 0:
            chd_price = UniversalBookingExtractor._get_dynamic_price(booking, 'child')
            amount = children * chd_price
            products.append({
                'no': row_number,
                'name': 'CHD',
                'quantity': children,
                'price': f"{chd_price:,.2f}",
                'amount': f"{amount:,.2f}",
                'category': 'passenger',
                'raw_price': chd_price,
                'raw_amount': amount
            })
            row_number += 1
        
        # Infants
        infants = getattr(booking, 'infants', 0) or 0
        if infants > 0:
            inf_price = UniversalBookingExtractor._get_dynamic_price(booking, 'infant')
            amount = infants * inf_price
            products.append({
                'no': row_number,
                'name': 'INF',
                'quantity': infants,
                'price': f"{inf_price:,.2f}",
                'amount': f"{amount:,.2f}",
                'category': 'passenger',
                'raw_price': inf_price,
                'raw_amount': amount
            })
            row_number += 1
            
        return products
    
    @staticmethod
    def _add_discounts_and_charges(booking, products):
        """เพิ่ม discounts และ additional charges"""
        row_number = len(products) + 1
        
        # ตรวจสอบ discount fields ต่างๆ
        discount_fields = [
            'discount_amount', 'additional_discount', 'promo_discount', 
            'early_bird_discount', 'group_discount', 'special_discount'
        ]
        
        for field in discount_fields:
            if hasattr(booking, field):
                amount = getattr(booking, field)
                if amount and float(amount) != 0:
                    amount_float = float(amount)
                    products.append({
                        'no': row_number,
                        'name': field.replace('_', ' ').title(),
                        'quantity': 1,
                        'price': f"{amount_float:,.2f}",
                        'amount': f"{amount_float:,.2f}",
                        'is_negative': amount_float < 0,
                        'category': 'discount',
                        'raw_price': amount_float,
                        'raw_amount': amount_float
                    })
                    row_number += 1
        
        # ตรวจสอบ additional charges
        charge_fields = [
            'service_charge', 'processing_fee', 'insurance_fee', 
            'fuel_surcharge', 'airport_tax', 'additional_charge'
        ]
        
        for field in charge_fields:
            if hasattr(booking, field):
                amount = getattr(booking, field)
                if amount and float(amount) > 0:
                    amount_float = float(amount)
                    products.append({
                        'no': row_number,
                        'name': field.replace('_', ' ').title(),
                        'quantity': 1,
                        'price': f"{amount_float:,.2f}",
                        'amount': f"{amount_float:,.2f}",
                        'category': 'charge',
                        'raw_price': amount_float,
                        'raw_amount': amount_float
                    })
                    row_number += 1
    
    @staticmethod
    def _get_dynamic_price(booking, passenger_type):
        """คำนวณราคาแบบ dynamic ตาม booking type และข้อมูลจริง"""
        
        # ลองหาราคาจาก booking fields ก่อน
        price_fields = {
            'adult': ['adult_price', 'price_per_adult', 'adt_price'],
            'child': ['child_price', 'price_per_child', 'chd_price'], 
            'infant': ['infant_price', 'price_per_infant', 'inf_price']
        }
        
        for field in price_fields.get(passenger_type, []):
            if hasattr(booking, field):
                price = getattr(booking, field)
                if price and float(price) > 0:
                    return float(price)
        
        # ถ้าไม่มีราคาแยก ให้คำนวณจาก total_amount
        if hasattr(booking, 'total_amount') and booking.total_amount:
            total_pax = (getattr(booking, 'adults', 0) or 0) + \
                       (getattr(booking, 'children', 0) or 0) + \
                       (getattr(booking, 'infants', 0) or 0)
            
            if total_pax > 0:
                avg_price = float(booking.total_amount) / total_pax
                
                # ปรับราคาตาม passenger type
                if passenger_type == 'adult':
                    return avg_price * 1.2  # Adult ราคาสูงกว่าเฉลี่ย
                elif passenger_type == 'child':
                    return avg_price * 0.7  # Child ลดราคา
                elif passenger_type == 'infant':
                    return avg_price * 0.1  # Infant ราคาต่ำ
        
        # Default prices ถ้าคำนวณไม่ได้
        defaults = {'adult': 5000.00, 'child': 2000.00, 'infant': 100.00}
        return defaults.get(passenger_type, 1000.00)
    
    @staticmethod
    def get_universal_total(booking):
        """คำนวณยอดรวมจาก booking แบบ universal - Smart Total Calculation"""
        
        # ลำดับการหายอดรวม
        total_fields = [
            'total_amount', 'grand_total', 'final_amount', 'final_total',
            'net_total', 'invoice_total', 'quote_total'
        ]
        
        for field in total_fields:
            if hasattr(booking, field):
                amount = getattr(booking, field)
                if amount and float(amount) > 0:
                    return float(amount)
        
        # คำนวณจาก products ถ้าหาไม่ได้
        products = UniversalBookingExtractor.extract_universal_products(booking)
        total = 0
        for product in products:
            try:
                raw_amount = product.get('raw_amount', 0)
                if raw_amount:
                    total += raw_amount
                else:
                    # Fallback to parsing formatted amount
                    amount_str = product['amount'].replace(',', '')
                    total += float(amount_str)
            except (ValueError, KeyError, TypeError):
                continue
                
        return total if total > 0 else 0.00
    
    @staticmethod
    def extract_customer_info(booking):
        """ดึงข้อมูลลูกค้าแบบ universal"""
        customer_info = {}
        
        # ถ้ามี customer relationship
        if hasattr(booking, 'customer') and booking.customer:
            customer = booking.customer
            customer_info.update({
                'name': getattr(customer, 'name', None) or getattr(customer, 'company_name', None),
                'phone': getattr(customer, 'phone', None) or getattr(customer, 'mobile', None),
                'email': getattr(customer, 'email', None),
                'address': getattr(customer, 'address', None),
                'company': getattr(customer, 'company_name', None)
            })
        
        # ถ้าไม่มี customer relationship ให้หาจาก booking fields
        else:
            name_fields = ['contact_name', 'party_name', 'customer_name', 'guest_name']
            phone_fields = ['contact_phone', 'customer_phone', 'phone_number', 'mobile']
            email_fields = ['contact_email', 'customer_email', 'email_address']
            
            for field in name_fields:
                if hasattr(booking, field) and getattr(booking, field):
                    customer_info['name'] = getattr(booking, field)
                    break
            
            for field in phone_fields:
                if hasattr(booking, field) and getattr(booking, field):
                    customer_info['phone'] = getattr(booking, field)
                    break
                    
            for field in email_fields:
                if hasattr(booking, field) and getattr(booking, field):
                    customer_info['email'] = getattr(booking, field)
                    break
        
        # Default values
        customer_info.setdefault('name', 'Customer Name')
        customer_info.setdefault('phone', '+66123456789')
        customer_info.setdefault('email', 'customer@example.com')
        
        return customer_info
    
    @staticmethod
    def get_products_summary(booking):
        """สรุปข้อมูล products สำหรับการแสดงผล"""
        products = UniversalBookingExtractor.extract_universal_products(booking)
        total = UniversalBookingExtractor.get_universal_total(booking)
        
        return {
            'products': products,
            'products_count': len(products),
            'grand_total': total,
            'formatted_total': f"{total:,.2f}",
            'currency': getattr(booking, 'currency', 'THB'),
            'has_discounts': any(p.get('is_negative', False) for p in products),
            'revenue_items': [p for p in products if not p.get('is_negative', False)],
            'discount_items': [p for p in products if p.get('is_negative', False)]
        }