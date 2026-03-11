export interface User {
  id: string;
  username: string | null;
  email: string;
  display_name: string;
  avatar_url: string | null;
  score: number;
  answers_count: number;
  is_admin: boolean;
  created_at: string;
}

export interface Poi {
  id: string;
  name: string;
  category: string;
  lat: number;
  lon: number;
  distance_meters: number;
}

export interface GpsPoint {
  lat: number;
  lon: number;
  timestamp: string | null;
}

export interface Question {
  question_id: string;
  gps_point: GpsPoint;
  candidates: Poi[];
}

export interface AnswerResponse {
  id: string;
  question_id: string;
  selected_poi_id: string;
  score_awarded: number;
  created_at: string;
}

export interface LeaderboardEntry {
  rank: number;
  display_name: string;
  avatar_url: string | null;
  score: number;
  answers_count: number;
}
