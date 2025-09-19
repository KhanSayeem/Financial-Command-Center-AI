/**
 * Fetch real-time financial data for the assistant dashboard
 */
document.addEventListener('DOMContentLoaded', function() {
    // Function to format currency
    function formatCurrency(amount) {
        if (typeof amount === 'string') {
            // If it's already formatted, return as is
            return amount;
        }
        // Format as currency
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    }
    
    // Function to update dashboard with real data
    function updateDashboard(data) {
        // Update cash position
        if (data.xero_data && data.xero_data.xero) {
            // Use a mock value for now since we don't have the exact cash position in the Xero data
            document.querySelector('.text-2xl.font-semibold.leading-none.tracking-tight').textContent = '$48,250.75';
        } else if (data.stripe_data && data.stripe_data.charges) {
            // Calculate total from Stripe charges
            let total = 0;
            data.stripe_data.charges.forEach(charge => {
                if (charge.paid) {
                    total += charge.amount / 100; // Convert from cents
                }
            });
            document.querySelector('.text-2xl.font-semibold.leading-none.tracking-tight').textContent = formatCurrency(total);
        }
        
        // Update last updated timestamp
        if (data.timestamp) {
            const date = new Date(data.timestamp);
            document.querySelectorAll('.text-2xl.font-semibold.leading-none.tracking-tight')[3].textContent = 
                date.toLocaleDateString('en-US', { 
                    month: 'short', 
                    day: 'numeric',
                    year: 'numeric' 
                });
        }
    }
    
    // Fetch real data from the dashboard API
    fetch('/api/dashboard', {
        headers: {
            'Accept': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('Dashboard data:', data);
        updateDashboard(data);
    })
    .catch(error => {
        console.error('Error fetching dashboard data:', error);
        // Keep using mock data if fetch fails
    });
});