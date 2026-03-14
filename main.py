from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI(title="Shopping Cart API", version="1.0.0")

# ============================================================================
# DATA MODELS
# ============================================================================

class CartItem(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: int
    subtotal: int

class CartResponse(BaseModel):
    items: List[CartItem]
    item_count: int
    grand_total: int

class Order(BaseModel):
    order_id: int
    customer_name: str
    product: str
    quantity: int
    unit_price: int
    total_price: int
    timestamp: str

class OrdersResponse(BaseModel):
    orders: List[Order]
    total_orders: int

class CheckoutRequest(BaseModel):
    customer_name: str
    delivery_address: str

# ============================================================================
# PRODUCTS DATABASE
# ============================================================================

PRODUCTS = {
    1: {"id": 1, "name": "Wireless Mouse", "price": 499, "in_stock": True},
    2: {"id": 2, "name": "Notebook", "price": 99, "in_stock": True},
    3: {"id": 3, "name": "USB Hub", "price": 299, "in_stock": False},
    4: {"id": 4, "name": "Pen Set", "price": 49, "in_stock": True},
}

# ============================================================================
# GLOBAL STATE
# ============================================================================

cart = []  # Shopping cart for current session
orders = []  # All orders placed
order_id_counter = 1  # Order ID auto-increment

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_subtotal(product: dict, quantity: int) -> int:
    """Calculate subtotal for a product."""
    return product["price"] * quantity

def get_product_by_id(product_id: int) -> dict:
    """Get product by ID or raise 404."""
    if product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail=f"Product with ID {product_id} not found")
    return PRODUCTS[product_id]

def check_product_stock(product: dict) -> None:
    """Check if product is in stock or raise 400."""
    if not product["in_stock"]:
        raise HTTPException(
            status_code=400,
            detail=f"{product['name']} is out of stock"
        )

def find_cart_item(product_id: int) -> Optional[int]:
    """Find cart item index by product_id. Returns None if not found."""
    for i, item in enumerate(cart):
        if item["product_id"] == product_id:
            return i
    return None

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
def home():
    """Root endpoint - API welcome message."""
    return {
        "message": "Welcome to Shopping Cart API",
        "endpoints": [
            "POST /cart/add - Add item to cart",
            "GET /cart - View cart",
            "DELETE /cart/{product_id} - Remove item from cart",
            "POST /cart/checkout - Checkout",
            "GET /orders - View all orders",
            "GET /docs - Swagger UI"
        ]
    }

# ============================================================================
# CART ENDPOINTS
# ============================================================================

@app.post("/cart/add")
def add_to_cart(product_id: int = Query(..., description="Product ID"),
                quantity: int = Query(..., description="Quantity to add")):
    """
    Add item to cart or update quantity if already exists.
    
    - **product_id**: ID of the product (1=Mouse, 2=Notebook, 3=USB Hub, 4=Pen Set)
    - **quantity**: Quantity to add
    """
    global cart
    
    # Validate product_id (will raise 404 if not found)
    product = get_product_by_id(product_id)
    
    # Check stock (will raise 400 if out of stock)
    check_product_stock(product)
    
    # Check if product already in cart
    cart_item_index = find_cart_item(product_id)
    
    if cart_item_index is not None:
        # Product exists in cart - update quantity
        cart[cart_item_index]["quantity"] += quantity
        cart[cart_item_index]["subtotal"] = calculate_subtotal(
            product, 
            cart[cart_item_index]["quantity"]
        )
        return {
            "message": "Cart updated",
            "cart_item": cart[cart_item_index]
        }
    else:
        # New product - add to cart
        subtotal = calculate_subtotal(product, quantity)
        new_item = {
            "product_id": product_id,
            "product_name": product["name"],
            "quantity": quantity,
            "unit_price": product["price"],
            "subtotal": subtotal
        }
        cart.append(new_item)
        return {
            "message": "Added to cart",
            "cart_item": new_item
        }

@app.get("/cart")
def view_cart():
    """View current shopping cart with grand total and item count."""
    global cart
    
    if not cart:
        return {"message": "Cart is empty"}
    
    grand_total = sum(item["subtotal"] for item in cart)
    item_count = len(cart)
    
    return {
        "items": cart,
        "item_count": item_count,
        "grand_total": grand_total
    }

@app.delete("/cart/{product_id}")
def remove_from_cart(product_id: int):
    """Remove item from cart by product_id."""
    global cart
    
    cart_item_index = find_cart_item(product_id)
    
    if cart_item_index is None:
        raise HTTPException(
            status_code=404,
            detail=f"Product {product_id} not found in cart"
        )
    
    removed_item = cart.pop(cart_item_index)
    
    if not cart:
        return {"message": f"Removed {removed_item['product_name']} from cart. Cart is now empty."}
    
    grand_total = sum(item["subtotal"] for item in cart)
    
    return {
        "message": f"Removed {removed_item['product_name']} from cart",
        "removed_item": removed_item,
        "updated_grand_total": grand_total,
        "item_count": len(cart)
    }

@app.post("/cart/checkout")
def checkout(checkout_data: CheckoutRequest):
    """
    Checkout the cart and create orders for each item.
    
    - **customer_name**: Name of the customer
    - **delivery_address**: Delivery address for the order
    """
    global cart, orders, order_id_counter
    
    # Validate cart is not empty
    if not cart:
        raise HTTPException(
            status_code=400,
            detail="Cart is empty — add items first"
        )
    
    # Create order for each item in cart
    checkout_orders = []
    grand_total = 0
    
    for item in cart:
        order = {
            "order_id": order_id_counter,
            "customer_name": checkout_data.customer_name,
            "product": item["product_name"],
            "quantity": item["quantity"],
            "unit_price": item["unit_price"],
            "total_price": item["subtotal"],
            "delivery_address": checkout_data.delivery_address,
            "timestamp": datetime.now().isoformat()
        }
        orders.append(order)
        checkout_orders.append(order)
        grand_total += item["subtotal"]
        order_id_counter += 1
    
    # Clear cart after checkout
    cart = []
    
    return {
        "message": "Checkout successful",
        "orders_placed": checkout_orders,
        "grand_total": grand_total,
        "customer_name": checkout_data.customer_name,
        "delivery_address": checkout_data.delivery_address
    }

# ============================================================================
# ORDERS ENDPOINT
# ============================================================================

@app.get("/orders")
def get_orders():
    """Get all orders placed so far."""
    if not orders:
        return {"orders": [], "total_orders": 0}
    
    return {
        "orders": orders,
        "total_orders": len(orders)
    }

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "OK", "message": "FastAPI Cart System is running"}
