// =====================================================================
//  mybetrecord — Azure deployment
//
//  Provisions a Container Apps environment, an Azure Container Registry,
//  a PostgreSQL Flexible Server, Log Analytics, and five container apps:
//  four internal microservices (auth, bets, reports, payments) plus the
//  externally-reachable frontend that reverse-proxies to them.
//
//  Why Container Apps and not bare Container Instances: ACA gives the
//  microservices internal DNS + managed ingress + independent scaling,
//  which is what "microservices architecture" actually needs. The same
//  images run on ACI if you prefer — see README for that path.
// =====================================================================

@description('Deployment location.')
param location string = resourceGroup().location

@description('Short prefix for resource names (lowercase, 3-11 chars).')
@minLength(3)
@maxLength(11)
param namePrefix string = 'mybetrec'

@description('Container image tag to deploy for every service.')
param imageTag string = 'latest'

@description('PostgreSQL administrator login.')
param pgAdminLogin string = 'betadmin'

@secure()
@description('PostgreSQL administrator password.')
param pgAdminPassword string

@secure()
@description('Secret used to sign JWTs (generate a long random string).')
param jwtSecret string

@description('Public origin(s) allowed by CORS. Use explicit https origins in prod.')
param corsOrigins string = 'https://www.mybetrecord.com,https://mybetrecord.com'

@secure()
@description('Stripe secret key (optional — leave blank to disable billing).')
param stripeSecretKey string = ''

@description('Existing Stripe Product id for Pro prices (optional).')
param stripeProductId string = ''

@description('Max bets a free user can enter per day (Pro is unlimited).')
param freeDailyBetLimit int = 5

@secure()
param stripeWebhookSecret string = ''

@description('Public site origin for password-reset links (e.g. https://www.mybetrecord.com).')
param frontendUrl string = ''

@description('SMTP server hostname (optional — leave blank to disable outbound email).')
param smtpHost string = ''

@description('SMTP server port.')
param smtpPort int = 587

@description('From address for outbound email.')
param smtpFrom string = 'noreply@mybetrecord.com'

@description('Use STARTTLS when connecting to SMTP (true/false).')
param smtpUseTls string = 'true'

@secure()
@description('SMTP username (optional).')
param smtpUser string = ''

@secure()
@description('SMTP password (optional).')
param smtpPassword string = ''

// ---------------------------------------------------------------------
var tags = { app: 'mybetrecord', managedBy: 'bicep' }
var acrName = toLower('${namePrefix}acr${uniqueString(resourceGroup().id)}')
var pgServerName = toLower('${namePrefix}-pg-${uniqueString(resourceGroup().id)}')
var pgDatabase = 'betrecord'
var envName = '${namePrefix}-env'
var lawName = '${namePrefix}-logs'

// ---------------------------------------------------------------------
//  Observability
// ---------------------------------------------------------------------
resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: lawName
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ---------------------------------------------------------------------
//  Container registry
// ---------------------------------------------------------------------
resource acr 'Microsoft.ContainerRegistry/registries@2023-11-01-preview' = {
  name: acrName
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: {
    adminUserEnabled: true // simplest path; switch to managed identity for prod
  }
}

// ---------------------------------------------------------------------
//  PostgreSQL Flexible Server
// ---------------------------------------------------------------------
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: pgServerName
  location: location
  tags: tags
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: pgAdminLogin
    administratorLoginPassword: pgAdminPassword
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
  }
}

resource pgDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: postgres
  name: pgDatabase
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Allow other Azure services (the Container Apps) to reach the DB.
// For production, prefer VNet integration + private endpoint over this rule.
resource pgFirewallAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: postgres
  name: 'AllowAllAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

var databaseUrl = 'postgresql+psycopg://${pgAdminLogin}:${pgAdminPassword}@${postgres.properties.fullyQualifiedDomainName}:5432/${pgDatabase}?sslmode=require'

// ---------------------------------------------------------------------
//  Container Apps environment
// ---------------------------------------------------------------------
resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: envName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: law.properties.customerId
        sharedKey: law.listKeys().primarySharedKey
      }
    }
  }
}

// ---------------------------------------------------------------------
//  Helper: shared config for a backend service
// ---------------------------------------------------------------------
var registryServer = acr.properties.loginServer
var acrCreds = acr.listCredentials()

var commonSecrets = [
  { name: 'database-url', value: databaseUrl }
  { name: 'jwt-secret', value: jwtSecret }
  { name: 'acr-password', value: acrCreds.passwords[0].value }
]

var commonEnv = [
  { name: 'DATABASE_URL', secretRef: 'database-url' }
  { name: 'JWT_SECRET', secretRef: 'jwt-secret' }
  { name: 'ENVIRONMENT', value: 'production' }
  { name: 'CORS_ORIGINS', value: corsOrigins }
  { name: 'FREE_DAILY_BET_LIMIT', value: string(freeDailyBetLimit) }
]

var registries = [
  {
    server: registryServer
    username: acrCreds.username
    passwordSecretRef: 'acr-password'
  }
]

var stripeSecrets = empty(stripeSecretKey)
  ? []
  : [
      { name: 'stripe-secret', value: stripeSecretKey }
      { name: 'stripe-webhook', value: stripeWebhookSecret }
    ]

var stripeEnv = empty(stripeSecretKey)
  ? []
  : [
      { name: 'STRIPE_SECRET_KEY', secretRef: 'stripe-secret' }
      { name: 'STRIPE_WEBHOOK_SECRET', secretRef: 'stripe-webhook' }
      { name: 'STRIPE_PRODUCT_ID', value: stripeProductId }
    ]

var smtpSecrets = empty(smtpHost)
  ? []
  : concat(
      empty(smtpUser) ? [] : [{ name: 'smtp-user', value: smtpUser }],
      empty(smtpPassword) ? [] : [{ name: 'smtp-password', value: smtpPassword }]
    )

var smtpEnv = empty(smtpHost)
  ? []
  : concat(
      [
        { name: 'SMTP_HOST', value: smtpHost }
        { name: 'SMTP_PORT', value: string(smtpPort) }
        { name: 'SMTP_FROM', value: smtpFrom }
        { name: 'SMTP_USE_TLS', value: smtpUseTls }
      ],
      empty(smtpUser) ? [] : [{ name: 'SMTP_USER', secretRef: 'smtp-user' }],
      empty(smtpPassword) ? [] : [{ name: 'SMTP_PASSWORD', secretRef: 'smtp-password' }]
    )

var frontendEnv = empty(frontendUrl)
  ? []
  : [{ name: 'FRONTEND_URL', value: frontendUrl }]

var authSecrets = concat(commonSecrets, smtpSecrets)
var authEnv = concat(commonEnv, frontendEnv, smtpEnv)

// ---------------------------------------------------------------------
//  Backend microservices (internal ingress)
// ---------------------------------------------------------------------
resource authApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-auth'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: { external: false, targetPort: 8001, transport: 'auto' }
      secrets: authSecrets
      registries: registries
    }
    template: {
      containers: [
        {
          name: 'auth'
          image: '${registryServer}/auth:${imageTag}'
          resources: { cpu: json('0.25'), memory: '0.5Gi' }
          env: authEnv
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

resource betsApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-bets'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: { external: false, targetPort: 8002, transport: 'auto' }
      secrets: commonSecrets
      registries: registries
    }
    template: {
      containers: [
        {
          name: 'bets'
          image: '${registryServer}/bets:${imageTag}'
          resources: { cpu: json('0.25'), memory: '0.5Gi' }
          env: commonEnv
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 5 }
    }
  }
}

resource reportsApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-reports'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: { external: false, targetPort: 8003, transport: 'auto' }
      secrets: commonSecrets
      registries: registries
    }
    template: {
      containers: [
        {
          name: 'reports'
          image: '${registryServer}/reports:${imageTag}'
          resources: { cpu: json('0.5'), memory: '1.0Gi' }
          env: commonEnv
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

resource paymentsApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-payments'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: { external: false, targetPort: 8004, transport: 'auto' }
      secrets: concat(commonSecrets, stripeSecrets)
      registries: registries
    }
    template: {
      containers: [
        {
          name: 'payments'
          image: '${registryServer}/payments:${imageTag}'
          resources: { cpu: json('0.25'), memory: '0.5Gi' }
          env: concat(commonEnv, stripeEnv)
        }
      ]
      scale: { minReplicas: 0, maxReplicas: 2 }
    }
  }
}

// ---------------------------------------------------------------------
//  Frontend (external ingress) — proxies to the internal service FQDNs
// ---------------------------------------------------------------------
resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-frontend'
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
        allowInsecure: false
      }
      secrets: [
        { name: 'acr-password', value: acrCreds.passwords[0].value }
      ]
      registries: registries
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: '${registryServer}/frontend:${imageTag}'
          resources: { cpu: json('0.25'), memory: '0.5Gi' }
          env: [
            { name: 'AUTH_UPSTREAM', value: 'https://${authApp.properties.configuration.ingress.fqdn}' }
            { name: 'BETS_UPSTREAM', value: 'https://${betsApp.properties.configuration.ingress.fqdn}' }
            { name: 'REPORTS_UPSTREAM', value: 'https://${reportsApp.properties.configuration.ingress.fqdn}' }
            { name: 'PAYMENTS_UPSTREAM', value: 'https://${paymentsApp.properties.configuration.ingress.fqdn}' }
          ]
        }
      ]
      scale: { minReplicas: 1, maxReplicas: 3 }
    }
  }
}

// ---------------------------------------------------------------------
//  Outputs
// ---------------------------------------------------------------------
output frontendUrl string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output acrLoginServer string = registryServer
output postgresFqdn string = postgres.properties.fullyQualifiedDomainName
