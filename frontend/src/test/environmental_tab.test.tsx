import '@testing-library/jest-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { EnvironmentalTab } from '../components/EnvironmentalTab';
import * as envApi from '../services/environmentalApi';
import type {
  IndrayaniMonitoringResponse,
  RiverHistoricalRecord,
  RiverStationReference,
  WeatherForecastResponse,
} from '../types/environmental';

describe('Real-Time Environmental Intelligence & Indrayani River UI', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockStations: RiverStationReference[] = [
    {
      station_id: 'MPCB-INDRAYANI-MOSHI-11',
      station_name: 'Indrayani River at Moshi',
      river_name: 'Indrayani',
      basin_name: 'Krishna Basin / Bhima Sub-basin',
      village: 'Moshi',
      taluka: 'Haveli',
      district: 'Pune',
      state: 'Maharashtra',
      country: 'India',
      latitude: 18.68365,
      longitude: 73.87855,
      station_type: 'WATER_QUALITY_MONITORING_REFERENCE',
      monitoring_body: 'Maharashtra Pollution Control Board (MPCB)',
      source_citation: 'MPCB Station 11, GEMS/MINARS 80, ecmpcb.in/envtdata/gemsminar80.php',
      telemetry_status: 'TELEMETRY_UNVERIFIED',
      telemetry_available: false,
      disclaimer: 'Verified geographical environmental monitoring reference — flood telemetry not verified.',
    },
    {
      station_id: 'INDRAYANI-DEHU-GHAT',
      station_name: 'Indrayani River at Dehu Ghat',
      river_name: 'Indrayani',
      basin_name: 'Krishna Basin / Bhima Sub-basin',
      village: 'Dehu',
      taluka: 'Haveli',
      district: 'Pune',
      state: 'Maharashtra',
      country: 'India',
      latitude: 18.718,
      longitude: 73.768,
      station_type: 'PILGRIMAGE_GHAT_REFERENCE',
      monitoring_body: 'Corridor Geographical Reference Point',
      source_citation: 'Dehu Nagar Panchayat & MPCB Corridor Reference',
      telemetry_status: 'TELEMETRY_UNAVAILABLE',
      telemetry_available: false,
      disclaimer: 'Pilgrimage ghat geographic marker. Flood telemetry not verified.',
    },
  ];

  const mockForecast: WeatherForecastResponse = {
    latitude: 18.68365,
    longitude: 73.87855,
    timezone: 'Asia/Kolkata',
    provider: 'Open-Meteo',
    attribution: 'Weather data by Open-Meteo.com (CC-BY 4.0)',
    fetched_timestamp: new Date().toISOString(),
    freshness_status: 'LIVE',
    current: {
      temperature_c: 27.5,
      relative_humidity_pct: 68,
      precipitation_mm: 1.2,
      rain_mm: 1.2,
      wind_speed_kmh: 14.5,
      wind_direction_deg: 240,
      weather_code: 61,
      weather_description: 'Slight rain',
      observation_timestamp: new Date().toISOString(),
      fetched_timestamp: new Date().toISOString(),
      quality_status: 'VERIFIED_OBSERVATION',
      freshness_status: 'LIVE',
    },
    hourly: [
      {
        timestamp: '2026-11-10T12:00:00Z',
        precipitation_mm: 1.2,
        rain_mm: 1.2,
        precipitation_probability_pct: 75,
        temperature_c: 27.5,
        wind_speed_kmh: 14.5,
      },
      {
        timestamp: '2026-11-10T13:00:00Z',
        precipitation_mm: 2.4,
        rain_mm: 2.4,
        precipitation_probability_pct: 85,
        temperature_c: 26.8,
        wind_speed_kmh: 16.0,
      },
    ],
    daily: [
      {
        date: '2026-11-10',
        precipitation_sum_mm: 8.5,
        precipitation_probability_max_pct: 85,
        wind_speed_max_kmh: 22.0,
        temp_max_c: 29.0,
        temp_min_c: 21.0,
      },
    ],
  };

  const mockIndrayani: IndrayaniMonitoringResponse = {
    river_name: 'Indrayani River',
    district: 'Pune',
    primary_reference_station: mockStations[0],
    corridor_stations: mockStations,
    local_weather: mockForecast.current,
    rainfall_forecast_24h_mm: 8.5,
    rainfall_probability_max_pct: 85,
    imd_warnings: {
      district: 'Pune',
      state: 'Maharashtra',
      provider_status: 'UNCONFIGURED_FALLBACK',
      warnings: [
        {
          warning_id: 'IMD-PUNE-ADVISORY-DEFAULT',
          district: 'Pune',
          state: 'Maharashtra',
          warning_level: 'YELLOW',
          warning_type: 'Thunderstorm with moderate rain',
          headline: 'Pune District: Watch / Be Updated',
          description: 'Isolated moderate rainfall and gusty winds anticipated across ghat sectors.',
          issued_by: 'India Meteorological Department (IMD) Pune',
          freshness_status: 'FORECAST',
        },
      ],
      fetched_timestamp: new Date().toISOString(),
      attribution: 'India Meteorological Department (IMD) District Advisory',
      disclaimer: 'Official district-level meteorological guidance.',
    },
    river_telemetry_status: 'Indrayani River telemetry currently unavailable.',
    river_gauge_reading: null,
    historical_records: [
      {
        station_id: 'MPCB-INDRAYANI-MOSHI-11',
        record_date: '2025-10-15',
        parameter_name: 'pH',
        measured_value: 7.4,
        unit: 'pH units',
        source_agency: 'MPCB Water Quality Survey',
        disclaimer: 'Surface-water laboratory sample.',
      },
      {
        station_id: 'MPCB-INDRAYANI-MOSHI-11',
        record_date: '2025-10-15',
        parameter_name: 'Dissolved Oxygen (DO)',
        measured_value: 5.6,
        unit: 'mg/L',
        source_agency: 'MPCB Water Quality Survey',
        disclaimer: 'Surface-water laboratory sample.',
      },
    ],
    data_freshness: 'LIVE',
    attribution: 'MPCB Station 11 & Open-Meteo Weather API',
    disclaimer:
      'Verified geographical environmental monitoring reference — flood telemetry not verified.',
    fetched_timestamp: new Date().toISOString(),
  };

  const mockHistory: RiverHistoricalRecord[] = mockIndrayani.historical_records;

  it('renders the environmental dashboard and mandatory scientific disclaimers', async () => {
    vi.spyOn(envApi, 'fetchIndrayaniStations').mockResolvedValue(mockStations);
    vi.spyOn(envApi, 'fetchWeatherForecast').mockResolvedValue(mockForecast);
    vi.spyOn(envApi, 'fetchIndrayaniMonitoring').mockResolvedValue(mockIndrayani);
    vi.spyOn(envApi, 'fetchIndrayaniHistory').mockResolvedValue(mockHistory);

    render(<EnvironmentalTab />);

    // Check title and context
    expect(
      screen.getByText(/Indrayani River Basin & Weather Surveillance/i),
    ).toBeTruthy();

    // Check scientific honesty notices
    await waitFor(() => {
      expect(
        screen.getByText(/Verified Geographical Environmental Reference/i),
      ).toBeTruthy();
      expect(
        screen.getByText(/FLOOD TELEMETRY NOT VERIFIED/i),
      ).toBeTruthy();
      expect(
        screen.getByText(/Indrayani River telemetry currently unavailable/i),
      ).toBeTruthy();
    });

    // Check Weather KPI values
    expect(screen.getByText('27.5')).toBeTruthy();
    expect(screen.getByText(/Slight rain/i)).toBeTruthy();
    expect(screen.getByText('8.5')).toBeTruthy(); // 24h expected rainfall

    // Check IMD warning
    expect(
      screen.getByText(/\[YELLOW\] Pune District: Watch \/ Be Updated/i),
    ).toBeTruthy();
  });

  it('allows switching location presets and updates coordinate display', async () => {
    vi.spyOn(envApi, 'fetchIndrayaniStations').mockResolvedValue(mockStations);
    vi.spyOn(envApi, 'fetchWeatherForecast').mockResolvedValue(mockForecast);
    vi.spyOn(envApi, 'fetchIndrayaniMonitoring').mockResolvedValue(mockIndrayani);
    vi.spyOn(envApi, 'fetchIndrayaniHistory').mockResolvedValue(mockHistory);

    render(<EnvironmentalTab />);

    const select = screen.getByLabelText(/Location Preset:/i);
    expect(select).toBeTruthy();

    // Change to Dehu Ghat
    fireEvent.change(select, { target: { value: 'dehu-ghat' } });

    await waitFor(() => {
      expect(screen.getByDisplayValue('18.718')).toBeTruthy();
      expect(screen.getByDisplayValue('73.768')).toBeTruthy();
    });
  });

  it('allows clicking a station to inspect its parameters', async () => {
    vi.spyOn(envApi, 'fetchIndrayaniStations').mockResolvedValue(mockStations);
    vi.spyOn(envApi, 'fetchWeatherForecast').mockResolvedValue(mockForecast);
    vi.spyOn(envApi, 'fetchIndrayaniMonitoring').mockResolvedValue(mockIndrayani);
    vi.spyOn(envApi, 'fetchIndrayaniHistory').mockResolvedValue(mockHistory);

    render(<EnvironmentalTab />);

    await waitFor(() => {
      expect(
        screen.getByText(/Station Reference/i),
      ).toBeTruthy();
    });

    // Verify historical parameters are displayed in the archive table
    expect(screen.getByText('Dissolved Oxygen (DO)')).toBeTruthy();
    expect(screen.getByText('5.6')).toBeTruthy();
  });

  it('displays error notice gracefully when backend data fetch fails', async () => {
    vi.spyOn(envApi, 'fetchIndrayaniStations').mockResolvedValue([]);
    vi.spyOn(envApi, 'fetchWeatherForecast').mockRejectedValue(
      new Error('Weather upstream unavailable'),
    );
    vi.spyOn(envApi, 'fetchIndrayaniMonitoring').mockRejectedValue(
      new Error('Telemetry service offline'),
    );
    vi.spyOn(envApi, 'fetchIndrayaniHistory').mockResolvedValue([]);

    render(<EnvironmentalTab />);

    await waitFor(() => {
      expect(screen.getByText(/Data Acquisition Error/i)).toBeTruthy();
      expect(
        screen.getByText(/Weather upstream unavailable/i),
      ).toBeTruthy();
    });
  });
});
