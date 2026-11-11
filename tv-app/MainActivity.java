package app.karaoke.tv;

import android.app.Activity;
import android.os.Bundle;
import android.view.WindowManager;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;

/** Full-screen browser for the karaoke TV page. The TV link is baked in by build.sh (assets/url.txt). */
public class MainActivity extends Activity {
    private WebView web;

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);  // songs start with sound, no remote click needed
        s.setUserAgentString(s.getUserAgentString() + " KaraokeTV");  // tv.html skips its Start button
        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onReceivedError(WebView v, WebResourceRequest req, WebResourceError err) {
                if (req.isForMainFrame()) v.postDelayed(v::reload, 5000);  // server not up yet: keep trying
            }
        });
        setContentView(web);
        web.loadUrl(url());
    }

    private String url() {
        try (BufferedReader r = new BufferedReader(new InputStreamReader(getAssets().open("url.txt"), "UTF-8"))) {
            return r.readLine().trim();
        } catch (IOException e) {
            return "about:blank";
        }
    }

    @Override
    protected void onDestroy() {
        web.destroy();
        super.onDestroy();
    }
}
