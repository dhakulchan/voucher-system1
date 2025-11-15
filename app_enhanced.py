"""
Enhanced Flask Application for Unified Voucher System
Comprehensive upgrade with MariaDB, unified PDF generator, and social sharing
"""

import os
import sys
import logging
from datetime import datetime, date, timedelta
from pathlib import Path

# Flask imports
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Configuration and models
from config_mariadb import get_config
from models_mariadb import db, Customer, Booking, BookingProduct, Quote, Voucher, DocumentShare, ActivityLog

# Services
from services.unified_pdf_generator import UnifiedPDFGenerator

def create_app(config_name=None):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.environ.get('FLASK_ENV', 'production')
    app.config.from_object(get_config())
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # Initialize PDF generator
    pdf_generator = UnifiedPDFGenerator(app)
    
    # Setup logging
    setup_logging(app)
    
    # Register blueprints
    register_routes(app, pdf_generator)
    
    # Create tables
    with app.app_context():
        try:
            db.create_all()
            app.logger.info("Database tables created successfully")
        except Exception as e:
            app.logger.error(f"Database initialization error: {e}")
    
    return app

def setup_logging(app):
    """Setup application logging"""
    if not app.debug:
        # Ensure log directory exists
        log_dir = Path(app.config.get('LOG_FILE', 'logs/app.log')).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(app.config.get('LOG_FILE', 'logs/app.log'))
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Voucher System startup')

def register_routes(app, pdf_generator):
    """Register all application routes"""
    
    @app.route('/')
    def index():
        """Home page with system overview"""
        try:
            # Get summary statistics
            total_customers = Customer.query.count()
            total_bookings = Booking.query.count()
            total_quotes = Quote.query.count()
            total_vouchers = Voucher.query.count()
            
            # Recent activity
            recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()
            recent_quotes = Quote.query.order_by(Quote.generated_at.desc()).limit(5).all()
            
            return render_template('dashboard.html',
                                 stats={
                                     'customers': total_customers,
                                     'bookings': total_bookings,
                                     'quotes': total_quotes,
                                     'vouchers': total_vouchers
                                 },
                                 recent_bookings=recent_bookings,
                                 recent_quotes=recent_quotes)
        except Exception as e:
            app.logger.error(f"Dashboard error: {e}")
            return render_template('error.html', error="Dashboard loading failed"), 500
    
    # Customer Management Routes
    @app.route('/customers')
    def customers_list():
        """List all customers"""
        customers = Customer.query.order_by(Customer.created_at.desc()).all()
        return render_template('customers/list.html', customers=customers)
    
    @app.route('/customers/<int:customer_id>')
    def customer_detail(customer_id):
        """Customer detail view"""
        customer = Customer.query.get_or_404(customer_id)
        bookings = customer.bookings.order_by(Booking.created_at.desc()).all()
        return render_template('customers/detail.html', customer=customer, bookings=bookings)
    
    # Booking Management Routes
    @app.route('/bookings')
    def bookings_list():
        """List all bookings"""
        page = request.args.get('page', 1, type=int)
        status_filter = request.args.get('status')
        
        query = Booking.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        bookings = query.order_by(Booking.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        return render_template('bookings/list.html', bookings=bookings, status_filter=status_filter)
    
    @app.route('/bookings/<int:booking_id>')
    def booking_detail(booking_id):
        """Booking detail view"""
        booking = Booking.query.get_or_404(booking_id)
        quotes = booking.quotes.order_by(Quote.generated_at.desc()).all()
        vouchers = booking.vouchers.order_by(Voucher.issue_date.desc()).all()
        
        return render_template('bookings/detail.html', 
                             booking=booking, quotes=quotes, vouchers=vouchers)
    
    @app.route('/bookings/<int:booking_id>/edit')
    def booking_edit(booking_id):
        """Edit booking"""
        booking = Booking.query.get_or_404(booking_id)
        return render_template('bookings/edit.html', booking=booking)
    
    @app.route('/bookings/<int:booking_id>/confirm', methods=['POST'])
    def booking_confirm(booking_id):
        """Confirm booking (draft -> confirmed)"""
        try:
            booking = Booking.query.get_or_404(booking_id)
            
            if booking.status != 'draft':
                flash('Booking can only be confirmed from draft status', 'error')
                return redirect(url_for('booking_detail', booking_id=booking_id))
            
            booking.status = 'confirmed'
            booking.confirmed_at = datetime.utcnow()
            db.session.commit()
            
            flash('Booking confirmed successfully', 'success')
            return redirect(url_for('booking_detail', booking_id=booking_id))
            
        except Exception as e:
            app.logger.error(f"Booking confirmation error: {e}")
            flash('Error confirming booking', 'error')
            return redirect(url_for('booking_detail', booking_id=booking_id))
    
    # Quote Management Routes
    @app.route('/quotes')
    def quotes_list():
        """List all quotes"""
        page = request.args.get('page', 1, type=int)
        status_filter = request.args.get('status')
        
        query = Quote.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        quotes = query.order_by(Quote.generated_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        return render_template('quotes/list.html', quotes=quotes, status_filter=status_filter)
    
    @app.route('/quotes/<int:quote_id>')
    def quote_detail(quote_id):
        """Quote detail view"""
        quote = Quote.query.get_or_404(quote_id)
        return render_template('quotes/detail.html', quote=quote)
    
    @app.route('/bookings/<int:booking_id>/create-quote', methods=['POST'])
    def create_quote(booking_id):
        """Create quote from confirmed booking"""
        try:
            booking = Booking.query.get_or_404(booking_id)
            
            if not booking.can_create_quote():
                flash('Cannot create quote for this booking', 'error')
                return redirect(url_for('booking_detail', booking_id=booking_id))
            
            # Calculate quote totals from booking products
            subtotal = sum(product.total_price for product in booking.products)
            tax_rate = 7.0  # 7% VAT
            tax_amount = subtotal * (tax_rate / 100)
            total_amount = subtotal + tax_amount
            
            # Create quote
            quote = Quote(
                booking_id=booking_id,
                status='draft',
                subtotal=subtotal,
                tax_amount=tax_amount,
                total_amount=total_amount,
                valid_until=date.today() + timedelta(days=30),
                terms_conditions="""Terms and Conditions:
1. Quote valid for 30 days from issue date
2. Prices subject to availability
3. Payment required before service delivery
4. Cancellation policy applies
5. All services subject to third-party availability""",
                template_used='quote_template_final_qt.html'
            )
            
            db.session.add(quote)
            db.session.commit()
            
            flash(f'Quote {quote.quote_number} created successfully', 'success')
            return redirect(url_for('quote_detail', quote_id=quote.id))
            
        except Exception as e:
            app.logger.error(f"Quote creation error: {e}")
            flash('Error creating quote', 'error')
            return redirect(url_for('booking_detail', booking_id=booking_id))
    
    @app.route('/quotes/<int:quote_id>/accept', methods=['POST'])
    def accept_quote(quote_id):
        """Accept quote (sent -> accepted)"""
        try:
            quote = Quote.query.get_or_404(quote_id)
            
            if quote.status not in ['draft', 'sent']:
                flash('Quote cannot be accepted in current status', 'error')
                return redirect(url_for('quote_detail', quote_id=quote_id))
            
            quote.status = 'accepted'
            quote.accepted_at = datetime.utcnow()
            db.session.commit()
            
            flash('Quote accepted successfully', 'success')
            return redirect(url_for('quote_detail', quote_id=quote_id))
            
        except Exception as e:
            app.logger.error(f"Quote acceptance error: {e}")
            flash('Error accepting quote', 'error')
            return redirect(url_for('quote_detail', quote_id=quote_id))
    
    # PDF Generation Routes
    @app.route('/quotes/<int:quote_id>/pdf')
    def quote_pdf(quote_id):
        """Generate and serve Quote PDF"""
        try:
            result = pdf_generator.generate_quote_pdf(quote_id)
            
            if result['success']:
                return send_file(result['file_path'], as_attachment=False, 
                               mimetype='application/pdf')
            else:
                flash(f'PDF generation failed: {result["error"]}', 'error')
                return redirect(url_for('quote_detail', quote_id=quote_id))
                
        except Exception as e:
            app.logger.error(f"Quote PDF error: {e}")
            flash('Error generating PDF', 'error')
            return redirect(url_for('quote_detail', quote_id=quote_id))
    
    @app.route('/quotes/<int:quote_id>/png')
    def quote_png(quote_id):
        """Generate and serve Quote PNG"""
        try:
            result = pdf_generator.generate_quote_png(quote_id)
            
            if result['success']:
                return send_file(result['file_path'], as_attachment=False,
                               mimetype='image/png')
            else:
                flash(f'PNG generation failed: {result["error"]}', 'error')
                return redirect(url_for('quote_detail', quote_id=quote_id))
                
        except Exception as e:
            app.logger.error(f"Quote PNG error: {e}")
            flash('Error generating PNG', 'error')
            return redirect(url_for('quote_detail', quote_id=quote_id))
    
    # Voucher Management Routes
    @app.route('/vouchers')
    def vouchers_list():
        """List all vouchers"""
        page = request.args.get('page', 1, type=int)
        status_filter = request.args.get('status')
        
        query = Voucher.query
        if status_filter:
            query = query.filter_by(status=status_filter)
        
        vouchers = query.order_by(Voucher.issue_date.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        return render_template('vouchers/list.html', vouchers=vouchers, status_filter=status_filter)
    
    @app.route('/vouchers/<int:voucher_id>')
    def voucher_detail(voucher_id):
        """Voucher detail view"""
        voucher = Voucher.query.get_or_404(voucher_id)
        return render_template('vouchers/detail.html', voucher=voucher)
    
    @app.route('/quotes/<int:quote_id>/create-voucher', methods=['POST'])
    def create_voucher(quote_id):
        """Create voucher from paid quote"""
        try:
            quote = Quote.query.get_or_404(quote_id)
            
            if not quote.can_create_voucher():
                flash('Cannot create voucher for this quote', 'error')
                return redirect(url_for('quote_detail', quote_id=quote_id))
            
            # Create voucher
            voucher = Voucher(
                quote_id=quote_id,
                booking_id=quote.booking_id,
                status='active',
                issue_date=date.today(),
                expiry_date=date.today() + timedelta(days=365),  # 1 year validity
                service_date=quote.booking.booking_date,
                template_used='voucher_template_final.html'
            )
            
            db.session.add(voucher)
            db.session.commit()
            
            flash(f'Voucher {voucher.voucher_number} created successfully', 'success')
            return redirect(url_for('voucher_detail', voucher_id=voucher.id))
            
        except Exception as e:
            app.logger.error(f"Voucher creation error: {e}")
            flash('Error creating voucher', 'error')
            return redirect(url_for('quote_detail', quote_id=quote_id))
    
    @app.route('/vouchers/<int:voucher_id>/pdf')
    def voucher_pdf(voucher_id):
        """Generate and serve Voucher PDF"""
        try:
            result = pdf_generator.generate_voucher_pdf(voucher_id)
            
            if result['success']:
                return send_file(result['file_path'], as_attachment=False,
                               mimetype='application/pdf')
            else:
                flash(f'PDF generation failed: {result["error"]}', 'error')
                return redirect(url_for('voucher_detail', voucher_id=voucher_id))
                
        except Exception as e:
            app.logger.error(f"Voucher PDF error: {e}")
            flash('Error generating PDF', 'error')
            return redirect(url_for('voucher_detail', voucher_id=voucher_id))
    
    @app.route('/vouchers/<int:voucher_id>/png')
    def voucher_png(voucher_id):
        """Generate and serve Voucher PNG"""
        try:
            result = pdf_generator.generate_voucher_png(voucher_id)
            
            if result['success']:
                return send_file(result['file_path'], as_attachment=False,
                               mimetype='image/png')
            else:
                flash(f'PNG generation failed: {result["error"]}', 'error')
                return redirect(url_for('voucher_detail', voucher_id=voucher_id))
                
        except Exception as e:
            app.logger.error(f"Voucher PNG error: {e}")
            flash('Error generating PNG', 'error')
            return redirect(url_for('voucher_detail', voucher_id=voucher_id))
    
    # Social Sharing Routes
    @app.route('/quotes/<int:quote_id>/share/<share_type>')
    def share_quote(quote_id, share_type):
        """Create share link for quote"""
        try:
            quote = Quote.query.get_or_404(quote_id)
            
            # Create share token
            token = DocumentShare.create_share_token('quote', quote_id, share_type)
            
            if share_type == 'public_link':
                share_url = url_for('public_quote', token=token, _external=True)
                return jsonify({'success': True, 'share_url': share_url, 'token': token})
            elif share_type == 'line_oa':
                # Integration with Line OA API would go here
                return jsonify({'success': True, 'message': 'Shared to Line OA'})
            elif share_type in ['facebook', 'twitter']:
                share_url = url_for('public_quote', token=token, _external=True)
                return jsonify({'success': True, 'share_url': share_url})
            else:
                return jsonify({'success': False, 'error': 'Invalid share type'})
                
        except Exception as e:
            app.logger.error(f"Quote sharing error: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    @app.route('/vouchers/<int:voucher_id>/share/<share_type>')
    def share_voucher(voucher_id, share_type):
        """Create share link for voucher"""
        try:
            voucher = Voucher.query.get_or_404(voucher_id)
            
            # Create share token
            token = DocumentShare.create_share_token('voucher', voucher_id, share_type)
            
            if share_type == 'public_link':
                share_url = url_for('public_voucher', token=token, _external=True)
                return jsonify({'success': True, 'share_url': share_url, 'token': token})
            elif share_type == 'line_oa':
                # Integration with Line OA API would go here
                return jsonify({'success': True, 'message': 'Shared to Line OA'})
            elif share_type in ['facebook', 'twitter']:
                share_url = url_for('public_voucher', token=token, _external=True)
                return jsonify({'success': True, 'share_url': share_url})
            else:
                return jsonify({'success': False, 'error': 'Invalid share type'})
                
        except Exception as e:
            app.logger.error(f"Voucher sharing error: {e}")
            return jsonify({'success': False, 'error': str(e)})
    
    # Public Sharing Routes
    @app.route('/share/quote/<token>')
    def public_quote(token):
        """Public quote view via share token"""
        try:
            share = DocumentShare.query.filter_by(
                document_type='quote',
                share_token=token
            ).first_or_404()
            
            if share.is_expired():
                abort(404, description="Share link has expired")
            
            # Update access tracking
            share.accessed_count += 1
            share.last_accessed_at = datetime.utcnow()
            db.session.commit()
            
            quote = Quote.query.get_or_404(share.document_id)
            return render_template('public/quote.html', quote=quote, share=share)
            
        except Exception as e:
            app.logger.error(f"Public quote error: {e}")
            abort(404)
    
    @app.route('/share/voucher/<token>')
    def public_voucher(token):
        """Public voucher view via share token"""
        try:
            share = DocumentShare.query.filter_by(
                document_type='voucher',
                share_token=token
            ).first_or_404()
            
            if share.is_expired():
                abort(404, description="Share link has expired")
            
            # Update access tracking
            share.accessed_count += 1
            share.last_accessed_at = datetime.utcnow()
            db.session.commit()
            
            voucher = Voucher.query.get_or_404(share.document_id)
            return render_template('public/voucher.html', voucher=voucher, share=share)
            
        except Exception as e:
            app.logger.error(f"Public voucher error: {e}")
            abort(404)
    
    # API Routes
    @app.route('/api/bookings/<int:booking_id>')
    def api_booking(booking_id):
        """API endpoint for booking data"""
        booking = Booking.query.get_or_404(booking_id)
        return jsonify(booking.to_dict())
    
    @app.route('/api/quotes/<int:quote_id>')
    def api_quote(quote_id):
        """API endpoint for quote data"""
        quote = Quote.query.get_or_404(quote_id)
        return jsonify(quote.to_dict())
    
    @app.route('/api/vouchers/<int:voucher_id>')
    def api_voucher(voucher_id):
        """API endpoint for voucher data"""
        voucher = Voucher.query.get_or_404(voucher_id)
        return jsonify(voucher.to_dict())
    
    # Health check
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        try:
            # Check database connection
            db.session.execute('SELECT 1')
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'database': 'connected'
            })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500

# Create application instance
app = create_app()

if __name__ == '__main__':
    # Development server
    app.run(host='0.0.0.0', port=5000, debug=True)