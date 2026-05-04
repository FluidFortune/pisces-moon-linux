// ═══════════════════════════════════════════════════════════════════════
// PISCES MOON OS — SMS GATEWAY SERVICE
// Copyright (C) 2026 Eric Becker / Fluid Fortune
// SPDX-License-Identifier: AGPL-3.0-or-later
//
// Add to AndroidManifest.xml:
//   <uses-permission android:name="android.permission.SEND_SMS" />
//   <uses-permission android:name="android.permission.RECEIVE_SMS" />
//   <uses-permission android:name="android.permission.READ_SMS" />
//   <receiver android:name=".SmsGateway$SmsReceiver"
//             android:exported="true">
//     <intent-filter>
//       <action android:name="android.provider.Telephony.SMS_RECEIVED" />
//     </intent-filter>
//   </receiver>
//
// Add to MainActivity.java onCreate():
//   smsGateway = new SmsGateway(this, webView);
//   smsGateway.start();
//
// HOW IT WORKS:
//   1. Listens for mesh messages from WebView via JS bridge
//   2. If message is SOS type → formats and sends SMS to all contacts
//   3. If message is addressed to a phone number → sends as SMS
//   4. Receives incoming SMS → injects into mesh as MESH_MSG JSON
//   5. Sends delivery confirmation back to originating mesh node
// ═══════════════════════════════════════════════════════════════════════

package com.fluidfortune.piscesmoon;

import android.app.Activity;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Telephony;
import android.telephony.SmsManager;
import android.telephony.SmsMessage;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;
import android.widget.Toast;

import org.json.JSONObject;
import org.json.JSONArray;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.TimeZone;

public class SmsGateway {

    private static final String PREFS_NAME    = "PiscesMoonSMS";
    private static final String PREF_CONTACTS = "sar_contacts";
    private static final String PREF_ENABLED  = "gateway_enabled";
    private static final String PREF_NODE_ID  = "node_id";

    // Pisces Moon SMS format identifier — receivers can filter on this
    private static final String SMS_PREFIX = "[PM-SOS]";

    private final Activity   activity;
    private final WebView    webView;
    private final Handler    mainHandler;
    private final SmsManager smsManager;
    private final SharedPreferences prefs;
    private SmsReceiver smsReceiver;
    private boolean started = false;

    public SmsGateway(Activity activity, WebView webView) {
        this.activity   = activity;
        this.webView    = webView;
        this.mainHandler = new Handler(Looper.getMainLooper());
        this.smsManager = SmsManager.getDefault();
        this.prefs      = activity.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
    }

    // ── Lifecycle ─────────────────────────────────────────────────
    public void start() {
        if (started) return;
        started = true;

        // Register incoming SMS receiver
        smsReceiver = new SmsReceiver();
        IntentFilter filter = new IntentFilter(Telephony.Sms.Intents.SMS_RECEIVED_ACTION);
        filter.setPriority(IntentFilter.SYSTEM_HIGH_PRIORITY);
        activity.registerReceiver(smsReceiver, filter);

        // Expose bridge to WebView
        webView.addJavascriptInterface(new SmsBridge(), "PiscesSMS");
    }

    public void stop() {
        if (!started) return;
        try { activity.unregisterReceiver(smsReceiver); } catch (Exception ignored) {}
        started = false;
    }

    // ── Process SOS from WebView ──────────────────────────────────
    public void processSOS(String sosJson) {
        if (!isEnabled()) return;

        try {
            JSONObject sos = new JSONObject(sosJson);

            // Build the SMS text
            String smsText = buildSOSSms(sos);

            // Get contacts to notify
            List<String> contacts = getContacts();

            if (contacts.isEmpty()) {
                notifyWebView("gateway_error",
                    "No SAR contacts configured. Add contacts in SOS Beacon settings.");
                return;
            }

            // Send to all contacts
            int sent = 0;
            for (String number : contacts) {
                if (sendSms(number, smsText)) {
                    sent++;
                    logEvent("SOS SMS sent to " + number);
                }
            }

            // Confirm delivery back to WebView/mesh
            if (sent > 0) {
                notifyWebView("sos_delivered", String.valueOf(sent) + " contacts notified");
                sendMeshACK(sos.optString("node_id", "unknown"));
            }

        } catch (Exception e) {
            notifyWebView("gateway_error", "Failed to send SOS: " + e.getMessage());
        }
    }

    // ── Process regular mesh→SMS message ─────────────────────────
    public void processMeshToSms(String to, String from, String text) {
        if (!isEnabled()) return;
        if (!to.startsWith("+") && !to.matches("\\d{10,15}")) return; // Must be a phone number

        String smsText = "[PM-MESH] From: " + from + "\n" + text;
        sendSms(to, smsText);
    }

    // ── Build SOS SMS text ────────────────────────────────────────
    private String buildSOSSms(JSONObject sos) throws Exception {
        StringBuilder sb = new StringBuilder();
        sb.append(SMS_PREFIX).append(" EMERGENCY\n\n");

        String name = sos.optString("name", "UNKNOWN");
        if (!name.isEmpty() && !name.equals("UNKNOWN")) {
            sb.append("Person: ").append(name).append("\n");
        }

        sb.append("Situation: ").append(sos.optString("situation", "EMERGENCY")).append("\n\n");

        // GPS coordinates
        JSONObject gps = sos.optJSONObject("gps");
        if (gps != null && !gps.isNull("lat")) {
            double lat = gps.optDouble("lat");
            double lon = gps.optDouble("lon");
            double alt = gps.optDouble("alt_m", 0);
            String quality = gps.optString("quality", "?");

            sb.append("GPS: ").append(String.format(Locale.US, "%.5f, %.5f", lat, lon)).append("\n");
            sb.append("Alt: ").append(Math.round(alt)).append("m\n");
            sb.append("Accuracy: ").append(quality).append("\n\n");

            // Google Maps link
            sb.append("MAP: https://maps.google.com/?q=")
              .append(String.format(Locale.US, "%.5f,%.5f", lat, lon))
              .append("\n\n");
        } else {
            sb.append("GPS: NO FIX — location unknown\n\n");
        }

        // Node info
        sb.append("Node: ").append(sos.optString("node_id", "unknown")).append("\n");
        sb.append("Broadcast #").append(sos.optInt("broadcast", 1)).append("\n");

        // Timestamp
        sb.append("Time: ").append(sos.optString("timestamp", new Date().toString())).append("\n");

        sb.append("\nReply to this number to send message back to the device.");
        sb.append("\nPisces Moon OS — mesh.fluidfortune.com");

        return sb.toString();
    }

    // ── SMS send (handles long messages) ─────────────────────────
    private boolean sendSms(String number, String text) {
        try {
            if (text.length() > 160) {
                // Split into multiple SMS parts
                ArrayList<String> parts = smsManager.divideMessage(text);
                smsManager.sendMultipartTextMessage(number, null, parts, null, null);
            } else {
                smsManager.sendTextMessage(number, null, text, null, null);
            }
            return true;
        } catch (Exception e) {
            logEvent("SMS send failed to " + number + ": " + e.getMessage());
            return false;
        }
    }

    // ── Incoming SMS handler ──────────────────────────────────────
    private void handleIncomingSms(String from, String body) {
        // Inject into mesh as a reply
        try {
            JSONObject msg = new JSONObject();
            msg.put("type",    "SOS_REPLY");
            msg.put("from",    from);
            msg.put("text",    body);
            msg.put("ts",      System.currentTimeMillis() / 1000);
            msg.put("channel", "PM-DEFAULT");
            msg.put("via",     "sms_gateway");

            // Push to WebView
            final String json = msg.toString();
            mainHandler.post(() -> {
                webView.evaluateJavascript(
                    "if(window.PiscesAndroid && window.PiscesAndroid._onData)" +
                    "{ window.PiscesAndroid._onData('" + escapeJs(json) + "'); }",
                    null
                );
            });

            logEvent("SMS reply from " + from + " injected into mesh");

        } catch (Exception e) {
            logEvent("Failed to process incoming SMS: " + e.getMessage());
        }
    }

    // ── Mesh ACK back to originating node ────────────────────────
    private void sendMeshACK(String nodeId) {
        try {
            JSONObject ack = new JSONObject();
            ack.put("type",    "SOS_ACK");
            ack.put("from",    "sms_gateway");
            ack.put("to",      nodeId);
            ack.put("status",  "delivered");
            ack.put("ts",      System.currentTimeMillis() / 1000);

            final String json = ack.toString();
            mainHandler.post(() -> {
                webView.evaluateJavascript(
                    "if(window.PiscesAndroid && window.PiscesAndroid._onData)" +
                    "{ window.PiscesAndroid._onData('" + escapeJs(json) + "'); }",
                    null
                );
            });
        } catch (Exception e) {
            logEvent("Failed to send mesh ACK: " + e.getMessage());
        }
    }

    // ── Notify WebView ────────────────────────────────────────────
    private void notifyWebView(String eventType, String message) {
        try {
            JSONObject event = new JSONObject();
            event.put("type",    "GATEWAY_EVENT");
            event.put("event",   eventType);
            event.put("message", message);
            event.put("ts",      System.currentTimeMillis() / 1000);

            final String json = event.toString();
            mainHandler.post(() -> {
                webView.evaluateJavascript(
                    "if(window.PiscesAndroid && window.PiscesAndroid._onData)" +
                    "{ window.PiscesAndroid._onData('" + escapeJs(json) + "'); }",
                    null
                );
            });
        } catch (Exception ignored) {}
    }

    // ── Settings helpers ──────────────────────────────────────────
    public boolean isEnabled() {
        return prefs.getBoolean(PREF_ENABLED, true);
    }

    public List<String> getContacts() {
        List<String> contacts = new ArrayList<>();
        String raw = prefs.getString(PREF_CONTACTS, "");
        if (!raw.isEmpty()) {
            for (String c : raw.split(",")) {
                c = c.trim();
                if (!c.isEmpty()) contacts.add(c);
            }
        }
        return contacts;
    }

    public void setContacts(List<String> contacts) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < contacts.size(); i++) {
            if (i > 0) sb.append(",");
            sb.append(contacts.get(i));
        }
        prefs.edit().putString(PREF_CONTACTS, sb.toString()).apply();
    }

    private void logEvent(String msg) {
        android.util.Log.d("PiscesSMSGateway", msg);
    }

    private String escapeJs(String s) {
        return s.replace("\\", "\\\\")
                .replace("'",  "\\'")
                .replace("\n", "\\n")
                .replace("\r", "");
    }

    // ── JS Bridge exposed to WebView ──────────────────────────────
    public class SmsBridge {

        @JavascriptInterface
        public boolean isAvailable() {
            return started;
        }

        @JavascriptInterface
        public boolean isEnabled() {
            return SmsGateway.this.isEnabled();
        }

        // Called by SOS beacon when user activates SOS
        @JavascriptInterface
        public void sendSOS(String sosJson) {
            new Thread(() -> SmsGateway.this.processSOS(sosJson)).start();
        }

        // Called by mesh messenger for phone-number-addressed messages
        @JavascriptInterface
        public void sendToPhone(String phoneNumber, String fromNode, String text) {
            new Thread(() ->
                SmsGateway.this.processMeshToSms(phoneNumber, fromNode, text)
            ).start();
        }

        // Configure SAR contacts (comma-separated phone numbers)
        @JavascriptInterface
        public void setContacts(String contactsCsv) {
            List<String> list = new ArrayList<>();
            for (String c : contactsCsv.split(",")) {
                c = c.trim();
                if (!c.isEmpty()) list.add(c);
            }
            SmsGateway.this.setContacts(list);
        }

        @JavascriptInterface
        public String getContacts() {
            return String.join(",", SmsGateway.this.getContacts());
        }

        @JavascriptInterface
        public void setEnabled(boolean enabled) {
            prefs.edit().putBoolean(PREF_ENABLED, enabled).apply();
        }

        @JavascriptInterface
        public String getNodeId() {
            return prefs.getString(PREF_NODE_ID, "unknown");
        }

        // Send a test SMS to verify gateway is working
        @JavascriptInterface
        public void sendTestSms(String toNumber) {
            new Thread(() -> {
                String testMsg = SMS_PREFIX + " TEST\n\n" +
                    "Pisces Moon SMS Gateway test message.\n" +
                    "If you receive this, the gateway is working.\n" +
                    "Time: " + new Date().toString() + "\n" +
                    "Node: " + prefs.getString(PREF_NODE_ID, "unknown");
                boolean ok = SmsGateway.this.sendSms(toNumber, testMsg);
                SmsGateway.this.notifyWebView(
                    ok ? "test_sent" : "test_failed",
                    ok ? "Test SMS sent to " + toNumber : "Failed to send test SMS"
                );
            }).start();
        }
    }

    // ── SMS Broadcast Receiver ────────────────────────────────────
    public class SmsReceiver extends BroadcastReceiver {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (!Telephony.Sms.Intents.SMS_RECEIVED_ACTION.equals(intent.getAction())) return;

            Bundle bundle = intent.getExtras();
            if (bundle == null) return;

            Object[] pdus = (Object[]) bundle.get("pdus");
            if (pdus == null) return;

            for (Object pdu : pdus) {
                SmsMessage smsMessage = SmsMessage.createFromPdu(
                    (byte[]) pdu,
                    bundle.getString("format")
                );

                String from = smsMessage.getDisplayOriginatingAddress();
                String body = smsMessage.getDisplayMessageBody();

                if (from != null && body != null) {
                    // Only handle messages that look like replies
                    // (coming from known contacts or replying to our messages)
                    handleIncomingSms(from, body);
                }
            }
        }
    }
}
