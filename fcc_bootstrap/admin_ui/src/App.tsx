import React from "react";

import { Badge } from "./components/ui/badge";
import { Button } from "./components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./components/ui/card";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./components/ui/table";

const TOKEN_STORAGE_KEY = "fcc-admin-token";

type LicenseStatus = "active" | "pending" | "expired";

interface License {
  id: string;
  issuedTo: string;
  seats: number;
  status: LicenseStatus;
  issuedAt: string;
  expiresAt: string;
  tokenPreview?: string;
  tier?: string;
  activationCount?: number;
}

interface IssueLicenseValues {
  email: string;
  clientName: string;
  seats: number;
  tier: string;
}

interface LoginValues {
  email: string;
  password: string;
  token?: string;
}

interface LoginResponse {
  ok: boolean;
  token?: string;
  error?: string;
  email?: string;
}

interface LicensesResponse {
  ok: boolean;
  licenses?: License[];
  error?: string;
}

interface CreateLicenseResponse {
  ok: boolean;
  license_key?: string;
  license?: License;
  error?: string;
}

const mockLicenses: License[] = [
  {
    id: "LIC-001",
    issuedTo: "Acme Corp",
    seats: 15,
    status: "active",
    issuedAt: "2025-01-12T16:30:00Z",
    expiresAt: "2026-01-12T16:30:00Z",
    tokenPreview: "acme-corp-2025...",
    tier: "pilot",
    activationCount: 11,
  },
  {
    id: "LIC-002",
    issuedTo: "Bright Financial",
    seats: 50,
    status: "pending",
    issuedAt: "2025-02-02T10:00:00Z",
    expiresAt: "2026-02-02T10:00:00Z",
    tokenPreview: "bright-fin-2025...",
    tier: "growth",
    activationCount: 0,
  },
  {
    id: "LIC-003",
    issuedTo: "Nimbus Bank",
    seats: 25,
    status: "expired",
    issuedAt: "2023-11-18T09:12:00Z",
    expiresAt: "2024-11-18T09:12:00Z",
    tokenPreview: "nimbus-2023...",
    tier: "pilot",
    activationCount: 25,
  },
];

function formatDate(date: string) {
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(date));
}

function StatusBadge({ status }: { status: LicenseStatus }) {
  const variant =
    status === "active"
      ? "default"
      : status === "pending"
      ? "secondary"
      : "destructive";

  return (
    <Badge variant={variant}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </Badge>
  );
}

function LoginCard({
  onSubmit,
  isLoading,
  error,
}: {
  onSubmit: (values: LoginValues) => Promise<void>;
  isLoading: boolean;
  error: string | null;
}) {
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [token, setToken] = React.useState("");

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit({ email, password, token: token || undefined });
  }

  return (
    <Card className="w-full max-w-md border-border">
      <CardHeader>
        <CardTitle>Sign in to manage licenses</CardTitle>
        <CardDescription>
          Use your admin credentials. Optionally include a temporary token for
          pilot customers.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setEmail(event.target.value)
              }
              placeholder="you@company.com"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setPassword(event.target.value)
              }
              placeholder="••••••••"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="token">Temporary token (optional)</Label>
            <Input
              id="token"
              value={token}
              onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                setToken(event.target.value)
              }
              placeholder="Paste issued token"
            />
          </div>
          {error ? (
            <p className="text-sm font-medium text-destructive">{error}</p>
          ) : null}
          <Button className="w-full" disabled={isLoading} type="submit">
            {isLoading ? "Signing in..." : "Sign in"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function SummaryCard({
  title,
  value,
  helper,
}: {
  title: string;
  value: string;
  helper?: string;
}) {
  return (
    <Card className="border-border">
      <CardHeader className="pb-2">
        <CardDescription>{title}</CardDescription>
        <CardTitle className="text-3xl">{value}</CardTitle>
      </CardHeader>
      {helper ? (
        <CardContent className="pt-0 text-sm text-muted-foreground">
          {helper}
        </CardContent>
      ) : null}
    </Card>
  );
}

function Dashboard({
  licenses,
  isLoading,
  lastSyncedAt,
  onRefresh,
  notice,
  onIssueLicense,
}: {
  licenses: License[];
  isLoading: boolean;
  lastSyncedAt: Date | null;
  onRefresh: () => Promise<void>;
  notice?: string | null;
  onIssueLicense: (values: IssueLicenseValues) => Promise<License>;
}) {
  const [isIssueOpen, setIsIssueOpen] = React.useState(false);
  const [issueEmail, setIssueEmail] = React.useState("");
  const [issueClientName, setIssueClientName] = React.useState("");
  const [issueSeats, setIssueSeats] = React.useState(5);
  const [issueTier, setIssueTier] = React.useState("pilot");
  const [issueError, setIssueError] = React.useState<string | null>(null);
  const [issueSuccess, setIssueSuccess] = React.useState<string | null>(null);
  const [isIssuing, setIsIssuing] = React.useState(false);

  const totalSeats = React.useMemo(
    () => licenses.reduce((sum, license) => sum + license.seats, 0),
    [licenses]
  );
  const active = licenses.filter((license) => license.status === "active")
    .length;
  const pending = licenses.filter((license) => license.status === "pending")
    .length;
  const expired = licenses.filter((license) => license.status === "expired")
    .length;

  const canSubmitIssue = Boolean(issueEmail.trim());

  const handleIssueSubmit = async (
    event: React.FormEvent<HTMLFormElement>
  ) => {
    event.preventDefault();
    setIssueError(null);
    setIssueSuccess(null);
    setIsIssuing(true);
    try {
      const issued = await onIssueLicense({
        email: issueEmail.trim(),
        clientName: issueClientName.trim(),
        seats: issueSeats,
        tier: issueTier,
      });
      setIssueSuccess(
        `Issued ${issued.tokenPreview ?? issued.id} for ${issued.issuedTo}.`
      );
      setIssueEmail("");
      setIssueClientName("");
      setIssueSeats(issued.seats);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Failed to issue license. Try again.";
      setIssueError(message);
    } finally {
      setIsIssuing(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2 border-b border-border pb-5 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Financial Command Center · License Admin
          </h1>
          <p className="text-sm text-muted-foreground">
            Review issued licenses, monitor seat usage, and issue new customer
            tokens.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => onRefresh()}
            disabled={isLoading}
          >
            {isLoading ? "Refreshing..." : "Refresh data"}
          </Button>
          <Button
            className="bg-foreground text-background hover:bg-foreground/90"
            onClick={() => {
              setIsIssueOpen((value) => !value);
              setIssueError(null);
              setIssueSuccess(null);
            }}
          >
            {isIssueOpen ? "Close form" : "Issue license"}
          </Button>
        </div>
      </header>

      {notice ? (
        <div className="rounded-md border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
          {notice}
        </div>
      ) : null}

      {isIssueOpen ? (
        <Card className="border-border">
          <CardHeader>
            <CardTitle>Issue a customer license</CardTitle>
            <CardDescription>
              Create a new license token and share it with a customer to unlock
              the admin tools.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleIssueSubmit}>
              <div className="sm:col-span-1 space-y-2">
                <Label htmlFor="issue-email">Customer email</Label>
                <Input
                  id="issue-email"
                  type="email"
                  required
                  value={issueEmail}
                  onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                    setIssueEmail(event.target.value)
                  }
                  placeholder="finance@example.com"
                />
              </div>
              <div className="sm:col-span-1 space-y-2">
                <Label htmlFor="issue-client">Customer organization (optional)</Label>
                <Input
                  id="issue-client"
                  value={issueClientName}
                  onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                    setIssueClientName(event.target.value)
                  }
                  placeholder="Acme Financial Services"
                />
              </div>
              <div className="sm:col-span-1 space-y-2">
                <Label htmlFor="issue-seats">Seats / activations</Label>
                <Input
                  id="issue-seats"
                  type="number"
                  min={1}
                  value={issueSeats}
                  onChange={(event: React.ChangeEvent<HTMLInputElement>) =>
                    setIssueSeats(
                      Math.max(1, Number.parseInt(event.target.value, 10) || 1)
                    )
                  }
                />
              </div>
              <div className="sm:col-span-1 space-y-2">
                <Label htmlFor="issue-tier">Plan tier</Label>
                <select
                  id="issue-tier"
                  value={issueTier}
                  onChange={(event: React.ChangeEvent<HTMLSelectElement>) =>
                    setIssueTier(event.target.value)
                  }
                  className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                >
                  <option value="pilot">Pilot</option>
                  <option value="growth">Growth</option>
                  <option value="enterprise">Enterprise</option>
                </select>
              </div>
              <div className="sm:col-span-2 flex flex-col space-y-2">
                {issueError ? (
                  <p className="text-sm font-medium text-destructive">
                    {issueError}
                  </p>
                ) : null}
                {issueSuccess ? (
                  <p className="text-sm font-medium text-emerald-600">
                    {issueSuccess}
                  </p>
                ) : null}
                <div className="flex gap-2">
                  <Button
                    type="submit"
                    className="bg-primary text-primary-foreground hover:bg-primary/90"
                    disabled={isIssuing || !canSubmitIssue}
                  >
                    {isIssuing ? "Issuing..." : "Create license"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setIsIssueOpen(false);
                      setIssueError(null);
                      setIssueSuccess(null);
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <SummaryCard
          title="Active licenses"
          value={active.toString()}
          helper="Confirmed customers with valid credentials."
        />
        <SummaryCard
          title="Pending activation"
          value={pending.toString()}
          helper="Awaiting customer confirmation or payment."
        />
        <SummaryCard
          title="Expired"
          value={expired.toString()}
          helper="Licenses requiring follow-up."
        />
        <SummaryCard
          title="Total seats issued"
          value={totalSeats.toString()}
          helper="Includes pending and expired seats."
        />
      </section>

      <Card className="border-border">
        <CardHeader className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Recent license activity</CardTitle>
            <CardDescription>
              {lastSyncedAt
                ? `Synced ${lastSyncedAt.toLocaleString()}`
                : "Showing the latest available data."}
            </CardDescription>
          </div>
          {isLoading ? (
            <Badge variant="outline">Updating…</Badge>
          ) : (
            <Badge variant="outline">Live</Badge>
          )}
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>License ID</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead className="text-right">Seats</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Tier</TableHead>
                <TableHead>Issued</TableHead>
                <TableHead>Expires</TableHead>
                <TableHead>Token</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {licenses.map((license) => (
                <TableRow key={license.id}>
                  <TableCell className="font-medium">{license.id}</TableCell>
                  <TableCell>{license.issuedTo}</TableCell>
                  <TableCell className="text-right">
                    {license.seats.toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={license.status} />
                  </TableCell>
                  <TableCell className="capitalize text-muted-foreground">
                    {license.tier ?? "pilot"}
                  </TableCell>
                  <TableCell>{formatDate(license.issuedAt)}</TableCell>
                  <TableCell>{formatDate(license.expiresAt)}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {license.tokenPreview ?? "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
            <TableCaption>
              Manage pilot programs, renewals, and revocations from this
              dashboard.
            </TableCaption>
          </Table>
          {licenses.length === 0 ? (
            <p className="pt-6 text-sm text-muted-foreground">
              No license records found. Issue a license to see it listed here.
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = React.useState(false);
  const [authToken, setAuthToken] = React.useState<string | null>(null);
  const [authError, setAuthError] = React.useState<string | null>(null);
  const [isSigningIn, setIsSigningIn] = React.useState(false);
  const [licenses, setLicenses] = React.useState<License[]>(mockLicenses);
  const [isLoadingLicenses, setIsLoadingLicenses] = React.useState(false);
  const [lastSyncedAt, setLastSyncedAt] = React.useState<Date | null>(null);

  const refreshLicenses = React.useCallback(
    async (tokenOverride?: string | null) => {
      setIsLoadingLicenses(true);
      const tokenToUse = tokenOverride ?? authToken;

      if (!tokenToUse) {
        setLicenses(mockLicenses);
        setLastSyncedAt(null);
        setAuthError(
          "Sign in with your admin credentials to load live license data. Showing mock data for preview."
        );
        setIsLoadingLicenses(false);
        return;
      }

      try {
        const response = await fetch("/api/licenses", {
          headers: { Authorization: `Bearer ${tokenToUse}` },
        });
        if (!response.ok) {
          if (response.status === 401) {
            window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
            setAuthToken(null);
            setIsAuthenticated(false);
            throw new Error("Your session expired. Please sign in again.");
          }
          throw new Error("Failed to fetch licenses from server.");
        }

        const payload = (await response.json()) as LicensesResponse;
        if (!payload.ok || !payload.licenses) {
          throw new Error(
            payload.error ?? "License API returned an unexpected response."
          );
        }

        setLicenses(payload.licenses);
        setLastSyncedAt(new Date());
        setAuthError(null);
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "Unable to reach the license server.";
        console.warn("[admin-ui] Falling back to mock license data.", error);
        setLicenses(mockLicenses);
        setLastSyncedAt(null);
        setAuthError(`${message} Showing mock data for local development.`);
      } finally {
        setIsLoadingLicenses(false);
      }
    },
    [authToken]
  );

  async function issueLicense(values: IssueLicenseValues): Promise<License> {
    if (!authToken) {
      throw new Error("Sign in required before issuing licenses.");
    }

    try {
      const response = await fetch("/api/admin/create_license", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          email: values.email,
          client_name: values.clientName,
          tier: values.tier,
          max_activations: values.seats,
        }),
      });

      const payload = (await response.json()) as CreateLicenseResponse;
      if (!response.ok || !payload.ok || !payload.license) {
        throw new Error(payload.error ?? "Unable to issue license.");
      }

      await refreshLicenses(authToken);
      return payload.license;
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Unexpected error while issuing license.";
      throw new Error(message);
    }
  }

  async function handleLogin(values: LoginValues) {
    setAuthError(null);
    setIsSigningIn(true);
    try {
      const response = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });
      if (!response.ok) {
        throw new Error("Unable to authenticate with the license server.");
      }
      const payload = (await response.json()) as LoginResponse;
      if (!payload.ok || !payload.token) {
        throw new Error(payload.error ?? "Login failed. Try again.");
      }

      window.sessionStorage.setItem(TOKEN_STORAGE_KEY, payload.token);
      setAuthToken(payload.token);
      setIsAuthenticated(true);
      await refreshLicenses(payload.token);
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Unexpected error while signing in.";
      window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
      setAuthToken(null);
      setIsAuthenticated(true);
      setLicenses(mockLicenses);
      setLastSyncedAt(null);
      setAuthError(
        `${message} Showing mock data for preview. Configure the backend credentials before deploying.`
      );
    } finally {
      setIsSigningIn(false);
    }
  }

  React.useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const storedToken = window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
    if (storedToken) {
      setAuthToken(storedToken);
      setIsAuthenticated(true);
      void refreshLicenses(storedToken);
    }
  }, [refreshLicenses]);

  React.useEffect(() => {
    if (isAuthenticated) {
      void refreshLicenses();
    }
  }, [isAuthenticated, refreshLicenses]);

  return (
    <div className="min-h-svh bg-background">
      <div className="mx-auto flex min-h-svh w-full max-w-6xl flex-col px-4 py-10 sm:px-8">
        {isAuthenticated ? (
          <Dashboard
            licenses={licenses}
            isLoading={isLoadingLicenses}
            lastSyncedAt={lastSyncedAt}
            onRefresh={() => refreshLicenses()}
            notice={authError}
            onIssueLicense={issueLicense}
          />
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <LoginCard
              error={authError}
              isLoading={isSigningIn}
              onSubmit={handleLogin}
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default App;

