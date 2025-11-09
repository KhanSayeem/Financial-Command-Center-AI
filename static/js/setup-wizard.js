let currentStep = 0; // 0 = welcome, 1 = Stripe, 2 = Plaid, 3 = Xero OAuth, 4 = Connect Xero
const totalSteps = 4;
let stripeConfigured = false;
let plaidConfigured = false;
let xeroConfigured = true;
let xeroOauthConnected = false;
let stripePollingInterval = null;
let plaidPollingInterval = null;
let plaidLinkHandler = null;

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
        // Always check connection when entering step 4, but silently first
        checkXeroConnection(true);

        // Set up periodic checking in case user completed OAuth in another tab
        const connectionCheckInterval = setInterval(() => {
            if (currentStep === 4 && !xeroOauthConnected) {
                checkXeroConnection(true); // Silent check
            } else {
                clearInterval(connectionCheckInterval);
            }
        }, 5000); // Check every 5 seconds

        // Clear interval after 5 minutes
        setTimeout(() => clearInterval(connectionCheckInterval), 300000);
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

function toggleButtonLoading(spinnerId, textId, loading) {
    const spinner = document.getElementById(spinnerId);
    const text = document.getElementById(textId);
    if (spinner) {
        spinner.style.display = loading ? 'inline-flex' : 'none';
    }
    if (text) {
        text.style.display = loading ? 'none' : 'inline';
    }
}

async function refreshStripeConnectionStatus(silent = false) {
    const status = document.getElementById('stripeStatus');
    try {
        const response = await fetch(buildApiUrl('/api/setup/stripe-connection'));
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const result = await response.json();
        stripeConfigured = Boolean(result.connected);
        if (stripeConfigured) {
            if (status) {
                status.textContent = 'Connected';
                status.className = 'inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-100 text-emerald-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
            }
            document.getElementById('stripeNext').disabled = false;
            if (!silent) {
                showMessage('stripe-messages', 'success', `Connected to Stripe${result.account_id ? ` (${result.account_id})` : ''}.`);
            }
            if (stripePollingInterval) {
                clearInterval(stripePollingInterval);
                stripePollingInterval = null;
            }
        } else {
            if (status) {
                status.textContent = 'Pending';
                status.className = 'inline-flex items-center gap-2 rounded-full border border-border/70 bg-muted/60 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground';
            }
            document.getElementById('stripeNext').disabled = true;
            if (!silent) {
                showMessage('stripe-messages', 'error', 'No Stripe account connected yet.');
            }
        }
    } catch (error) {
        if (!silent) {
            showMessage('stripe-messages', 'error', `Failed to verify Stripe connection: ${error.message}`);
        }
    }
}

function connectStripe() {
    toggleButtonLoading('stripeConnectSpinner', 'stripeConnectText', true);
    const status = document.getElementById('stripeStatus');
    if (status) {
        status.textContent = 'Authorizing...';
        status.className = 'inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-100 text-sky-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
    }
    const oauthUrl = buildApiUrl('/oauth/stripe/start?from=setup');
    const oauthWindow = window.open(oauthUrl, '_blank', 'noopener');
    toggleButtonLoading('stripeConnectSpinner', 'stripeConnectText', false);
    if (!oauthWindow) {
        if (status) {
            status.textContent = 'Pending';
            status.className = 'inline-flex items-center gap-2 rounded-full border border-border/70 bg-muted/60 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground';
        }
        showMessage('stripe-messages', 'error', 'Unable to open Stripe Connect. Allow pop-ups or open the connection URL manually.');
        return;
    }

    showMessage('stripe-messages', 'success', 'Stripe OAuth window opened. Complete the flow in the other tab, then return here.');
    if (stripePollingInterval) {
        clearInterval(stripePollingInterval);
    }
    stripePollingInterval = setInterval(() => refreshStripeConnectionStatus(true), 5000);
    setTimeout(() => {
        if (stripePollingInterval) {
            clearInterval(stripePollingInterval);
            stripePollingInterval = null;
        }
    }, 300000);
}

function skipStripe() {
    stripeConfigured = false;
    const status = document.getElementById('stripeStatus');
    if (status) {
        status.textContent = 'Skipped';
        status.className = 'inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-100 text-amber-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
    }
    document.getElementById('stripeNext').disabled = false;
    showMessage('stripe-messages', 'success', 'Stripe connection skipped. You can enable it later from the admin dashboard.');
}

async function refreshPlaidConnectionStatus(silent = false) {
    const status = document.getElementById('plaidStatus');
    try {
        const response = await fetch(buildApiUrl('/api/setup/plaid-connection'));
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const result = await response.json();
        plaidConfigured = Boolean(result.connected);
        if (plaidConfigured) {
            if (status) {
                status.textContent = 'Connected';
                status.className = 'inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-100 text-emerald-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
            }
            document.getElementById('plaidNext').disabled = false;
            if (!silent) {
                const institution = result.institution_name ? ` (${result.institution_name})` : '';
                showMessage('plaid-messages', 'success', `Plaid linked successfully${institution}.`);
            }
            if (plaidPollingInterval) {
                clearInterval(plaidPollingInterval);
                plaidPollingInterval = null;
            }
        } else {
            if (status) {
                status.textContent = 'Pending';
                status.className = 'inline-flex items-center gap-2 rounded-full border border-border/70 bg-muted/60 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground';
            }
            document.getElementById('plaidNext').disabled = true;
            if (!silent) {
                showMessage('plaid-messages', 'error', 'No Plaid item connected yet.');
            }
        }
    } catch (error) {
        if (!silent) {
            showMessage('plaid-messages', 'error', `Failed to verify Plaid connection: ${error.message}`);
        }
    }
}

function connectPlaid() {
    toggleButtonLoading('plaidConnectSpinner', 'plaidConnectText', true);
    fetch(buildApiUrl('/oauth/plaid/link-token'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
    })
        .then((response) => response.json())
        .then((result) => {
            if (!result.success) {
                throw new Error(result.error || 'Failed to create link token');
            }
            if (!window.Plaid || typeof window.Plaid.create !== 'function') {
                throw new Error('Plaid Link script not loaded. Refresh the page and try again.');
            }
            plaidLinkHandler = window.Plaid.create({
                token: result.link_token,
                onSuccess: (public_token, metadata) => finalizePlaidConnection(public_token, metadata?.institution),
                onExit: (err) => {
                    if (err) {
                        showMessage('plaid-messages', 'error', `Plaid link exited: ${err.error_code || err.display_message || err.message}`);
                    }
                },
            });
            plaidLinkHandler.open();
            if (plaidPollingInterval) {
                clearInterval(plaidPollingInterval);
            }
            plaidPollingInterval = setInterval(() => refreshPlaidConnectionStatus(true), 5000);
            setTimeout(() => {
                if (plaidPollingInterval) {
                    clearInterval(plaidPollingInterval);
                    plaidPollingInterval = null;
                }
            }, 300000);
        })
        .catch((error) => {
            showMessage('plaid-messages', 'error', `Unable to launch Plaid Link: ${error.message}`);
        })
        .finally(() => {
            toggleButtonLoading('plaidConnectSpinner', 'plaidConnectText', false);
        });
}

async function finalizePlaidConnection(publicToken, institution) {
    try {
        const response = await fetch(buildApiUrl('/oauth/plaid/exchange'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                public_token: publicToken,
                institution,
            }),
        });
        const result = await response.json();
        if (!result.success) {
            throw new Error(result.error || 'Public token exchange failed');
        }
        plaidConfigured = true;
        showMessage('plaid-messages', 'success', 'Plaid connection established. Fetching latest status...');
        refreshPlaidConnectionStatus(false);
    } catch (error) {
        showMessage('plaid-messages', 'error', `Failed to exchange Plaid token: ${error.message}`);
    }
}

function skipPlaid() {
    plaidConfigured = false;
    const status = document.getElementById('plaidStatus');
    if (status) {
        status.textContent = 'Skipped';
        status.className = 'inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-100 text-amber-700 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em]';
    }
    document.getElementById('plaidNext').disabled = false;
    showMessage('plaid-messages', 'success', 'Plaid integration skipped. Banking workflows remain available in demo mode.');
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
    const oauthUrl = buildApiUrl('/login?from=setup');
    const oauthWindow = window.open(oauthUrl, '_blank', 'noopener');
    if (!oauthWindow) {
        updateConnectXeroStatus('pending');
        showMessage('connect-xero-messages', 'error', 'Unable to open the Xero OAuth window. Allow pop-ups or open the connection URL manually: ' + oauthUrl);
        return;
    }
    showMessage('connect-xero-messages', 'success', 'Xero OAuth window opened. You will be redirected back here after completing the flow.');
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
                // Clear any existing messages and show success
                document.getElementById('connect-xero-messages').innerHTML = '';
                showMessage('connect-xero-messages', 'success', `Successfully connected to Xero!<br><strong>Tenant ID:</strong> ${result.tenant_id}<br>You can now finish the setup.`);
            }
        } else {
            updateConnectXeroStatus('pending');
            if (!silent) {
                const reason = result.error ? ` Details: ${result.error}` : '';
                showMessage('connect-xero-messages', 'error', `No active Xero connection detected.${reason} If you just completed the OAuth flow, please click "Check connection" or wait a moment for automatic detection.`);
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



function showCompletion(result) {
    document.querySelectorAll('.step').forEach((section) => {
        section.classList.remove('active');
        if (section.id !== 'completion') {
            section.style.display = 'none';
        }
    });
    const completion = document.getElementById('completion');
    if (completion) {
        completion.style.display = 'block';
        completion.classList.add('active');
    }
    currentStep = totalSteps;
    updateProgress();
    requestAnimationFrame(() => scrollToStep('completion'));
    const messageContainerId = 'completion-messages';
    if (result) {
        const successMessage = result.message || 'Configuration saved successfully.';
        if (successMessage) {
            showMessage(messageContainerId, 'success', successMessage);
        }
        if (Array.isArray(result.warnings) && result.warnings.length) {
            const container = document.getElementById(messageContainerId);
            if (container) {
                const warningAlert = document.createElement('div');
                warningAlert.className = 'rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800';
                warningAlert.setAttribute('role', 'alert');
                const warningsHtml = result.warnings.map((warning) => `<div>${warning}</div>`).join('');
                warningAlert.innerHTML = `
        <div class="flex items-start gap-3">
            <i data-lucide="alert-circle" class="h-4 w-4 flex-shrink-0"></i>
            <div class="space-y-1 text-sm leading-relaxed">${warningsHtml}</div>
        </div>
    `;
                container.appendChild(warningAlert);
                if (window.lucide) {
                    window.lucide.createIcons();
                }
            }
        }
    } else {
        const container = document.getElementById(messageContainerId);
        if (container) {
            container.innerHTML = '';
        }
    }
    if (window.lucide) {
        window.lucide.createIcons();
    }
}

async function finishSetup() {
    const messageContainer = document.getElementById('connect-xero-messages') ? 'connect-xero-messages' : 'completion-messages';
    try {
        // Debug: Check current state of configuration flags
        console.log('Setup completion debug:', {
            stripeConfigured: stripeConfigured,
            plaidConfigured: plaidConfigured,
            xeroConfigured: xeroConfigured,
            xeroOauthConnected: xeroOauthConnected
        });

        const hasStripeConfig = stripeConfigured;
        const hasPlaidConfig = plaidConfigured;
        const hasXeroConfig = xeroOauthConnected;

        console.log('Configuration detection:', {
            hasStripeConfig: hasStripeConfig,
            hasPlaidConfig: hasPlaidConfig,
            hasXeroConfig: hasXeroConfig
        });

        const configData = {
            stripe: hasStripeConfig ? {} : { skipped: true },
            plaid: hasPlaidConfig ? {} : { skipped: true },
            xero: hasXeroConfig ? {} : { skipped: true }
        };

        console.log('About to save config data:', JSON.stringify(configData, null, 2));

        const response = await fetch(buildApiUrl('/api/setup/save-config'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(configData)
        });

        const result = await response.json();

        if (result.success) {
            showCompletion(result);
            return;
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

    refreshStripeConnectionStatus(true);
    refreshPlaidConnectionStatus(true);
    checkXeroConnection(true);

    // Check if we're on step 4 from URL hash (e.g., #step4)
    const hash = window.location.hash;
    if (hash.startsWith('#step4')) {
        // Show setup steps and navigate to step 4
        document.getElementById('setupSteps').style.display = 'block';
        showStep(4);

        // Check for error parameter in URL
        if (hash.includes('error=oauth_failed')) {
            setTimeout(() => {
                showMessage('connect-xero-messages', 'error', 'OAuth authorization failed. Please try connecting to Xero again.');
                updateConnectXeroStatus('pending');
            }, 500);
        } else {
            // Wait a moment for page to settle, then check Xero connection
            setTimeout(() => {
                checkXeroConnection(false);
            }, 1000);
        }
    }
});

// Add window focus listener to check Xero connection when user returns from OAuth
window.addEventListener('focus', () => {
    refreshStripeConnectionStatus(true);
    refreshPlaidConnectionStatus(true);
    if (currentStep === 4 && !xeroOauthConnected) {
        setTimeout(() => {
            checkXeroConnection(false);
        }, 1000);
    }
});
