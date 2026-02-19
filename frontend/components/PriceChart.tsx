"use client";

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from "recharts";
import { formatPrice } from "@/lib/api";

interface PricePoint {
  date: string;   // "02/15" 형식
  price: number;
}

interface PriceChartProps {
  data: PricePoint[];
  currentPrice: number;
  minPrice?: number;
  avgPrice?: number;
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 px-3 py-2 text-xs shadow-sm">
      <p className="text-gray-400 mb-1">{label}</p>
      <p className="font-bold text-gray-900">{formatPrice(payload[0].value)}</p>
    </div>
  );
}

export default function PriceChart({ data, currentPrice, minPrice, avgPrice }: PriceChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-gray-50 border border-gray-100 rounded-sm p-4 text-center">
        <p className="text-xs text-gray-400">가격 히스토리 수집 중...</p>
        <p className="text-[10px] text-gray-300 mt-1">7일 후 차트가 표시됩니다</p>
      </div>
    );
  }

  if (data.length === 1) {
    return (
      <div className="bg-gray-50 border border-gray-100 rounded-sm p-4">
        <p className="text-xs text-gray-500 mb-2">가격 추이 (수집 1일차)</p>
        <div className="flex items-center gap-4">
          <div>
            <p className="text-[10px] text-gray-400">현재가</p>
            <p className="text-sm font-bold text-gray-900">{formatPrice(currentPrice)}</p>
          </div>
          <div className="text-gray-200 text-xl">|</div>
          <div>
            <p className="text-[10px] text-gray-400">수집 시작일</p>
            <p className="text-sm font-medium text-gray-600">{data[0].date}</p>
          </div>
        </div>
        <p className="text-[10px] text-gray-300 mt-2">데이터가 쌓이면 차트가 표시됩니다 (매일 자동 수집)</p>
      </div>
    );
  }

  const prices = data.map((d) => d.price);
  const yMin = Math.min(...prices) * 0.95;
  const yMax = Math.max(...prices) * 1.05;
  const isAtMin = currentPrice <= Math.min(...prices);

  return (
    <div>
      {/* 요약 배지 */}
      <div className="flex items-center gap-3 mb-3">
        {isAtMin && (
          <span className="text-[10px] bg-red-50 text-red-600 border border-red-100 px-2 py-0.5 font-bold">
            🔥 현재 역대 최저가
          </span>
        )}
        {minPrice && (
          <span className="text-[10px] text-gray-400">
            {data.length}일 최저 {formatPrice(minPrice)}
          </span>
        )}
        {avgPrice && (
          <span className="text-[10px] text-gray-400">
            평균 {formatPrice(avgPrice)}
          </span>
        )}
      </div>

      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={data} margin={{ top: 4, right: 4, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 10, fill: "#aaa" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            domain={[yMin, yMax]}
            tickFormatter={(v) => `${Math.round(v / 1000)}k`}
            tick={{ fontSize: 10, fill: "#aaa" }}
            tickLine={false}
            axisLine={false}
            width={36}
          />
          <Tooltip content={<CustomTooltip />} />
          {avgPrice && (
            <ReferenceLine
              y={avgPrice}
              stroke="#ddd"
              strokeDasharray="4 4"
              label={{ value: "평균", position: "right", fontSize: 9, fill: "#bbb" }}
            />
          )}
          <Line
            type="monotone"
            dataKey="price"
            stroke="#E31E24"
            strokeWidth={2}
            dot={{ fill: "#E31E24", r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
