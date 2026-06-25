"use client";

import { useCallback, useEffect, useState } from "react";

// All saved conversations live under one localStorage key (browser-only).
const STORAGE_KEY = "tinyguide.chats.v1";

/** One rendered turn in a conversation. */
export type ChatTurn =
  | { role: "user"; content: string }
  | {
      role: "assistant";
      content: string;
      isEmergency: boolean;
      recommendedActions: string[];
      citations: string[];
      model: string;
    };

/** A saved conversation. */
export interface Conversation {
  id: string;
  title: string;
  messages: ChatTurn[];
  updatedAt: number;
}

interface Store {
  conversations: Conversation[];
  activeId: string | null;
}

const EMPTY: Store = { conversations: [], activeId: null };

function newId(): string {
  return `c_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function titleFrom(messages: ChatTurn[]): string {
  const firstUser = messages.find((m) => m.role === "user");
  const text = firstUser?.content.trim() ?? "";
  if (!text) return "New chat";
  return text.length > 40 ? `${text.slice(0, 40)}…` : text;
}

/**
 * Manage multiple chat conversations persisted in the browser.
 *
 * Returns the conversation list plus actions to start, continue, update, and
 * delete chats. The active conversation's messages are the single source of
 * truth the chat UI renders.
 */
export function useConversations() {
  const [store, setStore] = useState<Store>(EMPTY);
  const [loaded, setLoaded] = useState(false);

  // Load once after mount (localStorage is client-only — SSR-safe this way).
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) setStore(JSON.parse(raw) as Store);
    } catch {
      /* corrupt/unavailable storage — start empty */
    }
    setLoaded(true);
  }, []);

  // Persist on every change (after the initial load).
  useEffect(() => {
    if (!loaded) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
    } catch {
      /* storage full/blocked — non-fatal */
    }
  }, [store, loaded]);

  const active =
    store.conversations.find((c) => c.id === store.activeId) ?? null;

  // Newest first for the list view.
  const conversations = [...store.conversations].sort(
    (a, b) => b.updatedAt - a.updatedAt
  );

  // Replace the active conversation's messages (creating it on first message).
  const setActiveMessages = useCallback((messages: ChatTurn[]) => {
    setStore((s) => {
      const now = Date.now();
      const hasActive =
        s.activeId !== null && s.conversations.some((c) => c.id === s.activeId);

      if (!hasActive) {
        const id = newId();
        return {
          activeId: id,
          conversations: [
            ...s.conversations,
            { id, title: titleFrom(messages), messages, updatedAt: now },
          ],
        };
      }

      return {
        activeId: s.activeId,
        conversations: s.conversations.map((c) =>
          c.id === s.activeId
            ? { ...c, messages, title: titleFrom(messages), updatedAt: now }
            : c
        ),
      };
    });
  }, []);

  // Start a fresh chat (created for real once the first message is sent).
  const newChat = useCallback(() => {
    setStore((s) => ({ ...s, activeId: null }));
  }, []);

  // Continue an existing chat.
  const selectChat = useCallback((id: string) => {
    setStore((s) => ({ ...s, activeId: id }));
  }, []);

  // Delete a chat.
  const deleteChat = useCallback((id: string) => {
    setStore((s) => ({
      activeId: s.activeId === id ? null : s.activeId,
      conversations: s.conversations.filter((c) => c.id !== id),
    }));
  }, []);

  return {
    loaded,
    conversations,
    activeId: store.activeId,
    activeMessages: active?.messages ?? [],
    setActiveMessages,
    newChat,
    selectChat,
    deleteChat,
  };
}
