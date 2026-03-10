export interface User {
  id: string;
  email: string;
  display_name: string;
  avatar_url: string | null;
  score: number;
  answers_count: number;
  is_admin: boolean;
  created_at: string;
}
