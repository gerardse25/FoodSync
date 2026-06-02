import apiClient from "./client";

export type ExpensesPeriod = "weekly" | "monthly" | "yearly";

export type CostSeriesPoint = {
  period: string;
  start_date: string;
  end_date: string;
  total: string;
  item_count: number;
};

export type CostSummaryResponse = {
  code: string;
  period: ExpensesPeriod;
  date_from?: string | null;
  date_to: string;
  total: string;
  item_count: number;
  series: CostSeriesPoint[];
};

export type CostMemberShare = {
  user_id: string;
  should_pay: string;
  paid: string;
  settled_paid: string;
  settled_received: string;
  balance: string;
};

export type CostTransfer = {
  from_user_id: string;
  to_user_id: string;
  amount: string;
};

export type CostSplitResponse = {
  code: string;
  date_from?: string | null;
  date_to: string;
  total: string;
  members: CostMemberShare[];
  transfers: CostTransfer[];
};

export type CreateCostSettlementPayload = {
  from_user_id: string;
  to_user_id: string;
  amount: string;
  date_from?: string | null;
  date_to?: string | null;
};

export type CreateCostSettlementResponse = {
  code: string;
  missatge: string;
  settlement: {
    id: number;
    from_user_id: string;
    to_user_id: string;
    amount: string;
    date_from?: string | null;
    date_to?: string | null;
    paid_at: string;
  };
  split: CostSplitResponse;
};

export const expensesService = {
  getSummary: async (params?: {
    period?: ExpensesPeriod;
    date_from?: string;
    date_to?: string;
  }): Promise<CostSummaryResponse> => {
    try {
      const response = await apiClient.get("/inventory/costs/summary", {
        params,
      });
      return response.data;
    } catch (error: any) {
      throw (
        error?.response?.data?.detail ||
        "No s'ha pogut carregar el resum de despeses"
      );
    }
  },

  getSplit: async (params?: {
    date_from?: string;
    date_to?: string;
  }): Promise<CostSplitResponse> => {
    try {
      const response = await apiClient.get("/inventory/costs/split", {
        params,
      });
      return response.data;
    } catch (error: any) {
      throw (
        error?.response?.data?.detail ||
        "No s'ha pogut carregar el repartiment de despeses"
      );
    }
  },

  createSettlement: async (
    payload: CreateCostSettlementPayload
  ): Promise<CreateCostSettlementResponse> => {
    try {
      const response = await apiClient.post(
        "/inventory/costs/settlements",
        payload
      );
      return response.data;
    } catch (error: any) {
      throw (
        error?.response?.data?.detail ||
        "No s'ha pogut registrar el pagament"
      );
    }
  },
};