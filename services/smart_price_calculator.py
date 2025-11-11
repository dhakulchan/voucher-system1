"""
Smart Price Calculator Utilities - ตรวจสอบและคำนวณราคาแบบอัจฉริยะ
"""

import logging
from decimal import Decimal
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class SmartPriceCalculator:
    """ระบบคำนวณราคาอัจฉริยะ - ตรวจสอบความถูกต้องและคำนวณใหม่"""
    
    @staticmethod
    def verify_product_calculations(products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """ตรวจสอบการคำนวณราคาในรายการ products"""
        verification_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'corrected_products': [],
            'original_total': 0,
            'corrected_total': 0
        }
        
        original_total = 0
        corrected_total = 0
        
        for product in products:
            try:
                # ดึงข้อมูลจาก product
                quantity = int(product.get('quantity', 1))
                raw_price = product.get('raw_price', 0)
                raw_amount = product.get('raw_amount', 0)
                
                # หาราคาจริง
                if raw_price:
                    unit_price = float(raw_price)
                else:
                    # ลองคำนวณจาก formatted price
                    price_value = product.get('price', 0)
                    if isinstance(price_value, (int, float)):
                        unit_price = float(price_value)
                    else:
                        price_str = str(price_value).replace(',', '')
                        unit_price = float(price_str) if price_str else 0
                
                # หายอดจริง
                if raw_amount:
                    actual_amount = float(raw_amount)
                else:
                    # ลองคำนวณจาก formatted amount
                    amount_value = product.get('amount', 0)
                    if isinstance(amount_value, (int, float)):
                        actual_amount = float(amount_value)
                    else:
                        amount_str = str(amount_value).replace(',', '')
                        actual_amount = float(amount_str) if amount_str else 0
                
                # คำนวณยอดที่ควรจะเป็น
                expected_amount = quantity * unit_price
                
                # เพิ่มเข้า totals
                original_total += actual_amount
                corrected_total += expected_amount
                
                # ตรวจสอบความถูกต้อง
                tolerance = 0.01  # ยอมให้ผิดพลาด 1 สตางค์
                if abs(actual_amount - expected_amount) > tolerance:
                    verification_result['is_valid'] = False
                    verification_result['errors'].append({
                        'product_no': product.get('no', '?'),
                        'name': product.get('name', 'Unknown'),
                        'expected_amount': expected_amount,
                        'actual_amount': actual_amount,
                        'difference': actual_amount - expected_amount
                    })
                
                # สร้าง corrected product
                corrected_product = product.copy()
                corrected_product.update({
                    'price': f"{unit_price:,.2f}",
                    'amount': f"{expected_amount:,.2f}",
                    'raw_price': unit_price,
                    'raw_amount': expected_amount,
                    'calculation_verified': True
                })
                verification_result['corrected_products'].append(corrected_product)
                
            except (ValueError, TypeError) as e:
                verification_result['errors'].append({
                    'product_no': product.get('no', '?'),
                    'name': product.get('name', 'Unknown'),
                    'error': f'Calculation error: {str(e)}'
                })
                verification_result['corrected_products'].append(product)
        
        verification_result['original_total'] = original_total
        verification_result['corrected_total'] = corrected_total
        
        return verification_result
    
    @staticmethod
    def calculate_smart_totals(booking, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """คำนวณยอดรวมอัจฉริยะ พร้อมแยกประเภท"""
        
        # แยกประเภทรายการ
        revenue_items = []
        discount_items = []
        charge_items = []
        
        for product in products:
            amount = product.get('raw_amount', 0)
            category = product.get('category', 'product')
            
            if amount < 0 or category == 'discount':
                discount_items.append(product)
            elif category in ['charge', 'fee', 'tax']:
                charge_items.append(product)
            else:
                revenue_items.append(product)
        
        # คำนวณยอดรวมแต่ละประเภท
        revenue_total = sum(p.get('raw_amount', 0) for p in revenue_items)
        discount_total = sum(p.get('raw_amount', 0) for p in discount_items)
        charge_total = sum(p.get('raw_amount', 0) for p in charge_items)
        
        subtotal = revenue_total
        total_after_discount = subtotal + discount_total  # discount_total is negative
        grand_total = total_after_discount + charge_total
        
        # ตรวจสอบกับยอดรวมจาก booking
        booking_total = 0
        if hasattr(booking, 'total_amount') and booking.total_amount:
            booking_total = float(booking.total_amount)
        
        return {
            'revenue_total': revenue_total,
            'discount_total': discount_total,
            'charge_total': charge_total,
            'subtotal': subtotal,
            'total_after_discount': total_after_discount,
            'grand_total': grand_total,
            'booking_total': booking_total,
            'totals_match': abs(grand_total - booking_total) < 0.01,
            'revenue_items': revenue_items,
            'discount_items': discount_items,
            'charge_items': charge_items,
            'formatted': {
                'revenue_total': f"{revenue_total:,.2f}",
                'discount_total': f"{discount_total:,.2f}",
                'charge_total': f"{charge_total:,.2f}",
                'subtotal': f"{subtotal:,.2f}",
                'total_after_discount': f"{total_after_discount:,.2f}",
                'grand_total': f"{grand_total:,.2f}",
                'booking_total': f"{booking_total:,.2f}"
            }
        }
    
    @staticmethod
    def smart_price_detection(booking) -> Dict[str, Any]:
        """ตรวจหาราคาอัจฉริยะ จากข้อมูลต่างๆ ใน booking"""
        
        price_sources = {}
        
        # ตรวจหาราคาจาก booking fields
        price_fields = [
            'total_amount', 'grand_total', 'final_amount', 'net_total',
            'adult_price', 'child_price', 'infant_price',
            'base_price', 'package_price', 'tour_price'
        ]
        
        for field in price_fields:
            if hasattr(booking, field):
                value = getattr(booking, field)
                if value and float(value) > 0:
                    price_sources[field] = {
                        'value': float(value),
                        'formatted': f"{float(value):,.2f}",
                        'source': 'booking_field'
                    }
        
        # ตรวจหาราคาจาก relationships
        if hasattr(booking, 'line_items') and booking.line_items:
            line_items_total = 0
            for item in booking.line_items:
                if hasattr(item, 'total_price') and item.total_price:
                    line_items_total += float(item.total_price)
            
            if line_items_total > 0:
                price_sources['line_items_total'] = {
                    'value': line_items_total,
                    'formatted': f"{line_items_total:,.2f}",
                    'source': 'line_items'
                }
        
        # ตรวจหาราคาจาก JSON fields
        json_fields = ['product_breakdown', 'pricing_details', 'cost_breakdown']
        for field in json_fields:
            if hasattr(booking, field):
                field_value = getattr(booking, field)
                if field_value:
                    try:
                        if isinstance(field_value, str):
                            import json
                            data = json.loads(field_value)
                        else:
                            data = field_value
                        
                        total = SmartPriceCalculator._extract_total_from_json(data)
                        if total > 0:
                            price_sources[f'{field}_total'] = {
                                'value': total,
                                'formatted': f"{total:,.2f}",
                                'source': f'json_{field}'
                            }
                    except:
                        pass
        
        # หาราคาที่น่าเชื่อถือที่สุด
        recommended_price = SmartPriceCalculator._find_most_reliable_price(price_sources)
        
        return {
            'price_sources': price_sources,
            'recommended_price': recommended_price,
            'sources_count': len(price_sources),
            'has_multiple_sources': len(price_sources) > 1
        }
    
    @staticmethod
    def _extract_total_from_json(data) -> float:
        """ดึงยอดรวมจาก JSON data"""
        total = 0
        
        if isinstance(data, dict):
            # หา total fields
            for key, value in data.items():
                if 'total' in key.lower() and isinstance(value, (int, float)):
                    total += float(value)
                elif isinstance(value, dict):
                    total += SmartPriceCalculator._extract_total_from_json(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            total += SmartPriceCalculator._extract_total_from_json(item)
        
        return total
    
    @staticmethod
    def _find_most_reliable_price(price_sources: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """หาราคาที่น่าเชื่อถือที่สุด"""
        
        if not price_sources:
            return None
        
        # ลำดับความน่าเชื่อถือ
        reliability_order = [
            'total_amount', 'grand_total', 'final_amount', 'net_total',
            'line_items_total', 'product_breakdown_total'
        ]
        
        for field in reliability_order:
            if field in price_sources:
                return {
                    'field': field,
                    'value': price_sources[field]['value'],
                    'formatted': price_sources[field]['formatted'],
                    'source': price_sources[field]['source'],
                    'reliability': 'high'
                }
        
        # ถ้าไม่มีใน reliability list ให้เลือกตัวแรก
        first_source = next(iter(price_sources.items()))
        return {
            'field': first_source[0],
            'value': first_source[1]['value'],
            'formatted': first_source[1]['formatted'],
            'source': first_source[1]['source'],
            'reliability': 'medium'
        }

class ProductDataExtractor:
    """เครื่องมือดึงข้อมูล Product แบบละเอียด"""
    
    @staticmethod
    def extract_complete_product_data(booking) -> Dict[str, Any]:
        """ดึงข้อมูล Product ครบถ้วน พร้อมการตรวจสอบ"""
        
        # ใช้ Universal Extractor
        from services.universal_booking_extractor import UniversalBookingExtractor
        
        # ใช้ booking.products หรือ extract จาก booking
        if hasattr(booking, 'products') and booking.products:
            products = booking.products
        else:
            products = []
        
        # Debug: Check products type
        logger.info(f"📋 Products type: {type(products)}")
        logger.info(f"📋 Products content: {products}")
        
        # Handle products data type
        if isinstance(products, str):
            try:
                import json
                products = json.loads(products)
                logger.info(f"📋 Parsed products from JSON string: {len(products)} items")
            except:
                logger.warning("⚠️ Could not parse products string as JSON, using empty list")
                products = []
        elif not isinstance(products, list):
            logger.warning(f"⚠️ Products is not a list: {type(products)}, using empty list")
            products = []
        
        # ตรวจสอบและแก้ไขการคำนวณ
        verification = SmartPriceCalculator.verify_product_calculations(products)
        
        # คำนวณยอดรวมอัจฉริยะ
        smart_totals = SmartPriceCalculator.calculate_smart_totals(booking, verification['corrected_products'])
        
        # ตรวจหาราคาอัจฉริยะ
        price_detection = SmartPriceCalculator.smart_price_detection(booking)
        
        return {
            'products': verification['corrected_products'],
            'verification': verification,
            'smart_totals': smart_totals,
            'price_detection': price_detection,
            'product_count': len(verification['corrected_products']),
            'calculation_status': 'verified' if verification['is_valid'] else 'corrected',
            'data_quality': ProductDataExtractor._assess_data_quality(verification, smart_totals, price_detection)
        }
    
    @staticmethod
    def _assess_data_quality(verification: Dict, smart_totals: Dict, price_detection: Dict) -> Dict[str, Any]:
        """ประเมินคุณภาพข้อมูล"""
        
        quality_score = 100
        issues = []
        
        # ตรวจสอบการคำนวณ
        if not verification['is_valid']:
            quality_score -= 20
            issues.append('Calculation errors found')
        
        # ตรวจสอบความสอดคล้องของยอดรวม
        if not smart_totals['totals_match']:
            quality_score -= 15
            issues.append('Totals do not match')
        
        # ตรวจสอบแหล่งข้อมูลราคา
        if price_detection['sources_count'] < 2:
            quality_score -= 10
            issues.append('Limited price sources')
        
        # ให้คะแนนระดับ
        if quality_score >= 90:
            grade = 'A'
        elif quality_score >= 80:
            grade = 'B'
        elif quality_score >= 70:
            grade = 'C'
        else:
            grade = 'D'
        
        return {
            'score': quality_score,
            'grade': grade,
            'issues': issues,
            'status': 'excellent' if grade == 'A' else 'good' if grade == 'B' else 'fair' if grade == 'C' else 'poor'
        }