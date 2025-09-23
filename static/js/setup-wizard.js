let currentStep = 0; // 0 = welcome, 1 = Stripe, 2 = Plaid, 3 = Xero OAuth, 4 = Connect Xero
const totalSteps = 4;
let stripeConfigured = false;
let plaidConfigured = false;
let xeroConfigured = false;
let xeroOauthConnected = false;

function updateProgress() {
    const progress = currentStep === 0 ? 0 : (currentStep / totalSteps) * 100;
    const fill = document.getElementById('progressFill');
    if (fill) {
        fill.style.width = progress + '%';
    }
    const label = document.getElementById('currentStepLabel');
    if (label) {
        label.textContent = currentStep;
    }
}

function beginSetup() {
    // Show the setup steps and scroll to them
    document.getElementById('setupSteps').style.display = 'block';
    currentStep = 1;
    showStep(1);
    // Smooth scroll to the setup steps
    setTimeout(() => {
        document.getElementById('setupSteps').scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    }, 100);
}

function scrollToStep(elementId) {
    const target = document.getElementById(elementId);
    if (!target) {
        return;
    }
    const offset = 80;
    const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - offset;
    window.scrollTo({ top: Math.max(targetPosition, 0), behavior: 'smooth' });
}

function showStep(step) {
    document.querySelectorAll('.step').forEach((section) => section.classList.remove('active'));
    const target = document.getElementById('step' + step);
    if (target) {
        target.classList.add('active');
        target.style.display = 'block';
    }
    currentStep = step;
    updateProgress();
    if (step === 4) {
        const finishButton = document.getElementById('connectXeroFinish');
        if (finishButton && !xeroOauthConnected) {
            finishButton.disabled = true;
        }
        checkXeroConnection(true);
    }
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

function nextStep() {
    if (currentStep < totalSteps) {
        const upcomingStep = currentStep + 1;
        showStep(upcomingStep);
        requestAnimationFrame(() => scrollToStep('step' + upcomingStep));
    } else {
        // Show completion
        document.querySelectorAll('.step').forEach((section) => section.classList.remove('active'));
        document.getElementById('completion').classList.add('active');
        document.getElementById('completion').style.display = 'block';
        currentStep = totalSteps;
        updateProgress();
        requestAnimationFrame(() => scrollToStep('completion'));
    }
}

function prevStep() {
    if (currentStep > 1) {
        showStep(currentStep - 1);
    }
}

function buildApiUrl(path) {
    try {
        const origin = window.location.origin || '';
        if (!origin || origin.startsWith('file:')) {
            return 'https://127.0.0.1:8000' + path;
        }
        return origin + path;
    } catch (e) {
        return 'https://127.0.0.1:8000' + path;
    }
}

function showMessage(containerId, type, message) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const wrapper = document.createElement('div');
    wrapper.className = type === 'error'
        ? 'rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700'
        : 'rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700';
    wrapper.setAttribute('role', 'alert');
    wrapper.innerHTML = `
        <div class="flex items-start gap-3">
            <i data-lucide="${type === 'error' ? 'alert-triangle' : 'check-circle'}" class="h-4 w-4 flex-shrink-0"></i>
            <div class="space-y-1 text-sm leading-relaxed">${message}</div>
        </div>
    `;
    container.innerHTML = '';
    container.appendChild(wrapper);
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

async function testStripeConnection() {
    const apiKey = document.getElementById('stripeApiKey').value;
    if (!apiKey) {
        showMessage('stripe-messages', 'error', 'Enter your Stripe secret key before testing.');
        return;
    }

    const testSpinner = document.getElementById('stripeTestSpinner');
    const testText = document.getElementById('stripeTestText');
    const status = document.getElementById('stripeStatus');

    status.textContent = 'Testing...';
    status.className = 'inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-100 text-sky-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';

    if (testSpinner && testText) {
        testSpinner.style.display = 'inline-flex';
        testText.style.display = 'none';
    }

    try {
        const response = await fetch(buildApiUrl('/api/setup/test-stripe'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                stripe_api_key: apiKey,
                stripe_publishable_key: document.getElementById('stripePublishableKey').value
            })
        });

        const result = await response.json();

        if (result.success) {
            stripeConfigured = true;
            status.textContent = 'Connected';
            status.className = 'inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-100 text-emerald-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
            document.getElementById('stripeNext').disabled = false;
            showMessage('stripe-messages', 'success', `Connected to Stripe successfully. Account: ${result.account_name || 'unknown'}.`);
        } else {
            throw new Error(result.error || 'Connection failed');
        }
    } catch (error) {
        status.textContent = 'Error';
        status.className = 'inline-flex items-center gap-2 rounded-full border border-rose-200 bg-rose-100 text-rose-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
        document.getElementById('stripeNext').disabled = true;
        showMessage('stripe-messages', 'error', `Stripe connection failed: ${error.message}`);
    } finally {
        if (testSpinner && testText) {
            testSpinner.style.display = 'none';
            testText.style.display = 'inline';
        }
    }
}

function skipStripe() {
    stripeConfigured = false;
    const status = document.getElementById('stripeStatus');
    status.textContent = 'Skipped';
    status.className = 'inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-100 text-amber-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
    document.getElementById('stripeNext').disabled = false;
    showMessage('stripe-messages', 'success', 'Stripe configuration skipped. You can enable it later from the admin dashboard.');
}

async function testPlaidConnection() {
    const clientId = document.getElementById('plaidClientId').value;
    const secret = document.getElementById('plaidSecret').value;
    const environment = document.getElementById('plaidEnvironment').value;

    if (!clientId || !secret) {
        showMessage('plaid-messages', 'error', 'Enter your Plaid client ID and secret before testing.');
        return;
    }

    const testSpinner = document.getElementById('plaidTestSpinner');
    const testText = document.getElementById('plaidTestText');
    const status = document.getElementById('plaidStatus');

    status.textContent = 'Testing...';
    status.className = 'inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-100 text-sky-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';

    if (testSpinner && testText) {
        testSpinner.style.display = 'inline-flex';
        testText.style.display = 'none';
    }

    try {
        const response = await fetch(buildApiUrl('/api/setup/test-plaid'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                plaid_client_id: clientId,
                plaid_secret: secret,
                plaid_environment: environment
            })
        });

        const result = await response.json();

        if (result.success) {
            plaidConfigured = true;
            status.textContent = 'Configured';
            status.className = 'inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-100 text-emerald-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
            document.getElementById('plaidNext').disabled = false;
            showMessage('plaid-messages', 'success', `Plaid credentials verified. Environment: ${result.environment || environment}.`);
        } else {
            throw new Error(result.error || 'Verification failed');
        }
    } catch (error) {
        plaidConfigured = false;
        status.textContent = 'Error';
        status.className = 'inline-flex items-center gap-2 rounded-full border border-rose-200 bg-rose-100 text-rose-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
        document.getElementById('plaidNext').disabled = true;
        showMessage('plaid-messages', 'error', `Plaid verification failed: ${error.message}`);
    } finally {
        if (testSpinner && testText) {
            testSpinner.style.display = 'none';
            testText.style.display = 'inline';
        }
    }
}

function skipPlaid() {
    plaidConfigured = false;
    const status = document.getElementById('plaidStatus');
    status.textContent = 'Skipped';
    status.className = 'inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-100 text-amber-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
    document.getElementById('plaidNext').disabled = false;
    showMessage('plaid-messages', 'success', 'Plaid integration skipped. Banking workflows remain available in demo mode.');
}

async function testXeroConnection() {
    const clientId = document.getElementById('xeroClientId').value;
    const clientSecret = document.getElementById('xeroClientSecret').value;

    if (!clientId || !clientSecret) {
        showMessage('xero-messages', 'error', 'Enter both the Xero client ID and secret.');
        return;
    }

    const testSpinner = document.getElementById('xeroTestSpinner');
    const testText = document.getElementById('xeroTestText');
    const status = document.getElementById('xeroStatus');

    status.textContent = 'Testing...';
    status.className = 'inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-100 text-sky-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';

    if (testSpinner && testText) {
        testSpinner.style.display = 'inline-flex';
        testText.style.display = 'none';
    }

    try {
        const response = await fetch(buildApiUrl('/api/setup/test-xero'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                xero_client_id: clientId,
                xero_client_secret: clientSecret
            })
        });

        const result = await response.json();

        if (result.success) {
            xeroConfigured = true;
            status.textContent = 'Connected';
            status.className = 'inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-100 text-emerald-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
            document.getElementById('xeroNext').disabled = false;
            showMessage('xero-messages', 'success', 'Xero credentials validated successfully.');
        } else {
            throw new Error(result.error || 'Validation failed');
        }
    } catch (error) {
        status.textContent = 'Error';
        status.className = 'inline-flex items-center gap-2 rounded-full border border-rose-200 bg-rose-100 text-rose-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
        document.getElementById('xeroNext').disabled = true;
        showMessage('xero-messages', 'error', `Xero validation failed: ${error.message}`);
    } finally {
        if (testSpinner && testText) {
            testSpinner.style.display = 'none';
            testText.style.display = 'inline';
        }
    }
}

function skipXero() {
    xeroConfigured = false;
    const status = document.getElementById('xeroStatus');
    status.textContent = 'Skipped';
    status.className = 'inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-100 text-amber-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
    document.getElementById('xeroNext').disabled = false;
    showMessage('xero-messages', 'success', 'Xero integration skipped. Demo mode will stay active until credentials are added.');
}



function updateConnectXeroStatus(state) {
    const status = document.getElementById('connectXeroStatus');
    if (!status) {
        return;
    }
    if (state === 'connected') {
        status.textContent = 'Connected';
        status.className = 'inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-100 text-emerald-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
    } else if (state === 'authorizing') {
        status.textContent = 'Authorizing...';
        status.className = 'inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-100 text-sky-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
    } else if (state === 'skipped') {
        status.textContent = 'Skipped';
        status.className = 'inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-100 text-amber-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
    } else {
        status.textContent = 'Pending';
        status.className = 'inline-flex items-center gap-2 rounded-full border border-border/70 bg-muted/60 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground';
    }
}

function launchXeroOAuth() {
    updateConnectXeroStatus('authorizing');
    const finishButton = document.getElementById('connectXeroFinish');
    if (finishButton) {
        finishButton.disabled = true;
    }
    const oauthUrl = buildApiUrl('/login');
    const oauthWindow = window.open(oauthUrl, '_blank', 'noopener');
    if (!oauthWindow) {
        updateConnectXeroStatus('pending');
        showMessage('connect-xero-messages', 'error', 'Unable to open the Xero OAuth window. Allow pop-ups or open the connection URL manually: ' + oauthUrl);
        return;
    }
    showMessage('connect-xero-messages', 'success', 'Xero OAuth window opened. Complete the flow, then return to verify the connection.');
}

async function checkXeroConnection(silent = false) {
    const finishButton = document.getElementById('connectXeroFinish');
    try {
        const response = await fetch(buildApiUrl('/api/setup/xero-connection'));
        if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`);
        }
        const result = await response.json();
        const isConnected = Boolean(result.connected && result.tenant_id);
        xeroOauthConnected = isConnected;
        if (finishButton) {
            finishButton.disabled = !isConnected;
        }
        if (isConnected) {
            updateConnectXeroStatus('connected');
            if (!silent) {
                showMessage('connect-xero-messages', 'success', `Connected to Xero tenant ${result.tenant_id}.`);
            }
        } else {
            updateConnectXeroStatus('pending');
            if (!silent) {
                const reason = result.error ? ` Details: ${result.error}` : '';
                showMessage('connect-xero-messages', 'error', `No active Xero connection detected.${reason} Authorize the application and select a tenant, then check again.`);
            }
        }
    } catch (error) {
        if (finishButton) {
            finishButton.disabled = true;
        }
        updateConnectXeroStatus('pending');
        if (!silent) {
            showMessage('connect-xero-messages', 'error', `Failed to verify Xero connection: ${error.message}`);
        }
    }
}

function skipXeroConnect() {
    xeroOauthConnected = false;
    const finishButton = document.getElementById('connectXeroFinish');
    if (finishButton) {
        finishButton.disabled = false;
    }
    updateConnectXeroStatus('skipped');
    showMessage('connect-xero-messages', 'success', 'Skipped Xero OAuth connection. You can finish setup now and connect later from the health dashboard.');
}



async function finishSetup() {
    const messageContainer = (currentStep >= 4 && document.getElementById('connect-xero-messages')) ? 'connect-xero-messages' : 'xero-messages';
    try {
        const configData = {
            stripe: stripeConfigured ? {
                api_key: document.getElementById('stripeApiKey').value,
                publishable_key: document.getElementById('stripePublishableKey').value
            } : { skipped: true },
            plaid: plaidConfigured ? {
                client_id: document.getElementById('plaidClientId').value,
                secret: document.getElementById('plaidSecret').value,
                environment: document.getElementById('plaidEnvironment').value
            } : { skipped: true },
            xero: xeroConfigured ? {
                client_id: document.getElementById('xeroClientId').value,
                client_secret: document.getElementById('xeroClientSecret').value
            } : { skipped: true }
        };

        const response = await fetch(buildApiUrl('/api/setup/save-config'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(configData)
        });

        const result = await response.json();

        if (result.success) {
            // Redirect to health check or dashboard after successful setup
            const redirectUrl = result.redirect_url || '/health';
            window.location.href = redirectUrl;
        } else {
            throw new Error(result.error || 'Configuration save failed');
        }
    } catch (error) {
        showMessage(messageContainer, 'error', `Save failed: ${error.message}`);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    updateProgress();
    if (window.lucide) {
        window.lucide.createIcons();
    }
});
