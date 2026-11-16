static ArrayList<Product> products = new ArrayList<>();
static ArrayList<Product> cart = new ArrayList<>();
static double balance = 5000;

static {
    products.add(new Product("Laptop", 50000, 5));
    products.add(new Product("Phone", 25000, 10));
    products.add(new Product("Headphones", 2000, 3));
    products.add(new Product("Keyboard", 1500, 0));
}

static Product searchProduct(String name) throws ProductNotFoundException {
    for (Product p : products) {
        if (p.name.equalsIgnoreCase(name)) {
            return p;
        }
    }
    throw new ProductNotFoundException("Product not found.");
}

static void addToCart(String name)
        throws ProductNotFoundException, OutOfStockException {

    Product p = searchProduct(name);

    if (p.stock <= 0) {
        throw new OutOfStockException("Product is out of stock.");
    }

    cart.add(p);
    p.stock--;

    System.out.println("Product added to cart.");
}

static void removeFromCart(String name) throws ProductNotFoundException {
    for (Product p : cart) {
        if (p.name.equalsIgnoreCase(name)) {
            cart.remove(p);
            p.stock++;
            System.out.println("Product removed from cart.");
            return;
        }
    }

    throw new ProductNotFoundException("Product is not present in cart.");
}

static void showCart() throws EmptyCartException {
    if (cart.isEmpty()) {
        throw new EmptyCartException("Cart is empty.");
    }

    double total = 0;

    System.out.println("\nCart:");

    for (Product p : cart) {
        System.out.println(p.name + " - Rs." + p.price);
        total += p.price;
    }

    System.out.println("Total = Rs." + total);
}

static void payment(double amount, String method)
        throws InvalidPaymentException, InsufficientFundsException {

    if (amount <= 0) {
        throw new InvalidPaymentException("Invalid payment amount.");
    }

    if (!method.equalsIgnoreCase("cash")
            && !method.equalsIgnoreCase("card")) {
        throw new InvalidPaymentException("Invalid payment method.");
    }

    if (method.equalsIgnoreCase("card") && amount > balance) {
        throw new InsufficientFundsException("Insufficient funds.");
    }

    if (method.equalsIgnoreCase("card")) {
        balance -= amount;
    }

    System.out.println("Payment successful.");
}

static void placeOrder()
        throws EmptyCartException,
        InvalidPaymentException,
        InsufficientFundsException {

    if (cart.isEmpty()) {
        throw new EmptyCartException("Cannot place order. Cart is empty.");
    }

    double total = 0;

    for (Product p : cart) {
        total += p.price;
    }

    payment(total, "card");

    cart.clear();

    System.out.println("Order placed successfully.");
}

public static void main(String[] args) {

    Scanner sc = new Scanner(System.in);

    while (true) {

        System.out.println("\n1. Search Product");
        System.out.println("2. Add Product");
        System.out.println("3. Remove Product");
        System.out.println("4. Show Cart");
        System.out.println("5. Place Order");
        System.out.println("6. Exit");

        System.out.print("Enter choice: ");
        int choice = sc.nextInt();
        sc.nextLine();

        try {

            switch (choice) {

                case 1:
                    System.out.print("Enter product name: ");
                    String search = sc.nextLine();

                    Product p = searchProduct(search);

                    System.out.println(
                            "Product: " + p.name +
                            ", Price: Rs." + p.price +
                            ", Stock: " + p.stock
                    );
                    break;

                case 2:
                    System.out.print("Enter product name: ");
                    String add = sc.nextLine();

                    addToCart(add);
                    break;

                case 3:
                    System.out.print("Enter product name: ");
                    String remove = sc.nextLine();

                    removeFromCart(remove);
                    break;

                case 4:
                    showCart();
                    break;

                case 5:
                    showCart();
                    placeOrder();
                    break;

                case 6:
                    System.out.println("Thank you.");
                    sc.close();
                    return;

                default:
                    System.out.println("Invalid choice.");
            }

        } catch (ProductNotFoundException e) {
            System.out.println("Product Error: " + e.getMessage());

        } catch (OutOfStockException e) {
            System.out.println("Stock Error: " + e.getMessage());

        } catch (InvalidPaymentException e) {
            System.out.println("Payment Error: " + e.getMessage());

        } catch (InsufficientFundsException e) {
            System.out.println("Payment Error: " + e.getMessage());

        } catch (EmptyCartException e) {
            System.out.println("Order Error: " + e.getMessage());

        } catch (ApplicationException e) {
            System.out.println("Application Error: " + e.getMessage());
        }
    }
}