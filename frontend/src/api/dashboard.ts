import { http } from './http'

export interface DashboardMetrics {
  my_mail_accounts: number
  public_mail_accounts: number
  today_fetches: number
  today_failed_fetches: number
  recent_errors: Array<{
    trace_id: string
    email: string
    error_code: string | null
    error_message: string | null
    created_at: string | null
  }>
  global_users?: number
  global_mail_accounts?: number
  global_api_keys?: number
  global_today_fetches?: number
  global_today_failed_fetches?: number
}

export function fetchDashboardMetrics() {
  return http.get<DashboardMetrics>('/api/dashboard')
}
