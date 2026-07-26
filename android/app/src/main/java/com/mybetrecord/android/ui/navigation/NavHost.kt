package com.mybetrecord.android.ui.navigation

import android.app.Activity
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Assessment
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.mybetrecord.android.data.repository.AuthRepository
import com.mybetrecord.android.ui.age.AgeAttestationScreen
import com.mybetrecord.android.ui.age.AgeViewModel
import com.mybetrecord.android.ui.auth.AuthScreen
import com.mybetrecord.android.ui.auth.ForgotPasswordScreen
import com.mybetrecord.android.ui.bets.BetEditorScreen
import com.mybetrecord.android.ui.bets.BetsListScreen
import com.mybetrecord.android.ui.dashboard.DashboardScreen
import com.mybetrecord.android.ui.reports.ReportsScreen
import com.mybetrecord.android.ui.settings.SettingsScreen
import dagger.hilt.EntryPoint
import dagger.hilt.InstallIn
import dagger.hilt.android.EntryPointAccessors
import dagger.hilt.components.SingletonComponent

object Routes {
    const val AUTH = "auth"
    const val FORGOT_PASSWORD = "forgot-password"
    const val DASHBOARD = "dashboard"
    const val BETS = "bets"
    const val BET_EDIT = "bets/{betId}"
    const val REPORTS = "reports"
    const val SETTINGS = "settings"

    fun betEdit(betId: String) = "bets/$betId"
}

private data class Tab(val route: String, val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector)

@EntryPoint
@InstallIn(SingletonComponent::class)
interface AuthRepositoryEntryPoint {
    fun authRepository(): AuthRepository
}

@Composable
fun MyBetRecordNavHost() {
    val ageViewModel: AgeViewModel = hiltViewModel()
    val ageAttested by ageViewModel.ageAttested.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val authRepository = EntryPointAccessors.fromApplication(
        context.applicationContext,
        AuthRepositoryEntryPoint::class.java,
    ).authRepository()

    when (ageAttested) {
        null -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            CircularProgressIndicator()
        }
        false -> AgeAttestationScreen(
            onConfirmed = {},
            onDeclined = { (context as? Activity)?.finish() },
            onConfirmClick = ageViewModel::confirmAge,
        )
        true -> {
            val start = if (authRepository.isLoggedIn()) Routes.DASHBOARD else Routes.AUTH
            AppNav(startDestination = start)
        }
    }
}

@Composable
private fun AppNav(startDestination: String) {
    val navController = rememberNavController()
    val tabs = listOf(
        Tab(Routes.DASHBOARD, "Home", Icons.Default.Home),
        Tab(Routes.BETS, "Bets", Icons.Default.List),
        Tab(Routes.REPORTS, "Reports", Icons.Default.Assessment),
        Tab(Routes.SETTINGS, "Settings", Icons.Default.Settings),
    )

    NavHost(navController = navController, startDestination = startDestination) {
        composable(Routes.AUTH) {
            AuthScreen(
                onLoggedIn = {
                    navController.navigate(Routes.DASHBOARD) {
                        popUpTo(Routes.AUTH) { inclusive = true }
                    }
                },
                onForgotPassword = { navController.navigate(Routes.FORGOT_PASSWORD) },
            )
        }
        composable(Routes.FORGOT_PASSWORD) {
            ForgotPasswordScreen(
                onBackToSignIn = { navController.popBackStack() },
            )
        }
        composable(Routes.DASHBOARD) {
            MainScaffold(
                tabs = tabs,
                currentRoute = Routes.DASHBOARD,
                onTabSelected = { route ->
                    navController.navigate(route) {
                        popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                        launchSingleTop = true
                        restoreState = true
                    }
                },
            ) { padding ->
                DashboardScreen(padding = padding)
            }
        }
        composable(Routes.BETS) {
            MainScaffold(
                tabs = tabs,
                currentRoute = Routes.BETS,
                onTabSelected = { route ->
                    navController.navigate(route) {
                        popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                        launchSingleTop = true
                        restoreState = true
                    }
                },
            ) { padding ->
                BetsListScreen(
                    padding = padding,
                    onOpenBet = { id -> navController.navigate(Routes.betEdit(id)) },
                    onCreateBet = { navController.navigate(Routes.betEdit("new")) },
                )
            }
        }
        composable(
            route = Routes.BET_EDIT,
            arguments = listOf(navArgument("betId") { type = NavType.StringType }),
        ) {
            BetEditorScreen(onDone = { navController.popBackStack() })
        }
        composable(Routes.REPORTS) {
            MainScaffold(
                tabs = tabs,
                currentRoute = Routes.REPORTS,
                onTabSelected = { route ->
                    navController.navigate(route) {
                        popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                        launchSingleTop = true
                        restoreState = true
                    }
                },
            ) { padding ->
                ReportsScreen(padding = padding)
            }
        }
        composable(Routes.SETTINGS) {
            MainScaffold(
                tabs = tabs,
                currentRoute = Routes.SETTINGS,
                onTabSelected = { route ->
                    navController.navigate(route) {
                        popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                        launchSingleTop = true
                        restoreState = true
                    }
                },
            ) { padding ->
                SettingsScreen(
                    padding = padding,
                    onLoggedOut = {
                        navController.navigate(Routes.AUTH) {
                            popUpTo(0) { inclusive = true }
                        }
                    },
                )
            }
        }
    }
}

@Composable
private fun MainScaffold(
    tabs: List<Tab>,
    currentRoute: String,
    onTabSelected: (String) -> Unit,
    content: @Composable (androidx.compose.foundation.layout.PaddingValues) -> Unit,
) {
    Scaffold(
        bottomBar = {
            NavigationBar {
                tabs.forEach { tab ->
                    NavigationBarItem(
                        selected = currentRoute == tab.route,
                        onClick = { onTabSelected(tab.route) },
                        icon = { Icon(tab.icon, contentDescription = tab.label) },
                        label = { Text(tab.label) },
                    )
                }
            }
        },
        content = content,
    )
}
