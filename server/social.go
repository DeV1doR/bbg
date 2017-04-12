package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"

	log "github.com/Sirupsen/logrus"

	"github.com/gorilla/mux"
	"github.com/gorilla/sessions"
	"golang.org/x/oauth2"
	"golang.org/x/oauth2/facebook"
	"golang.org/x/oauth2/github"
)

var (
	store      = sessions.NewCookieStore([]byte(appConf.SecretKey))
	oauth2conf = map[string]*oauth2.Config{
		"github": &oauth2.Config{
			ClientID:     appConf.Oauth2.Github.ClientID,
			ClientSecret: appConf.Oauth2.Github.ClientSecret,
			RedirectURL:  prepareRedirectURL("github"),
			Endpoint:     github.Endpoint,
		},
		"facebook": &oauth2.Config{
			ClientID:     appConf.Oauth2.Facebook.ClientID,
			ClientSecret: appConf.Oauth2.Facebook.ClientSecret,
			RedirectURL:  prepareRedirectURL("facebook"),
			Endpoint:     facebook.Endpoint,
		},
	}
)

func prepareRedirectURL(name string) string {
	return fmt.Sprintf("http://localhost:4000/login/%s/callback", name)
}

func serveSocialLogin(w http.ResponseWriter, r *http.Request) {
	name := mux.Vars(r)["social"]

	conf, ok := oauth2conf[name]
	if !ok {
		w.WriteHeader(http.StatusNotFound)
		return
	}

	url := conf.AuthCodeURL("state", oauth2.AccessTypeOffline)

	http.Redirect(w, r, url, 301)
}

func serveSocialLoginCallback(w http.ResponseWriter, r *http.Request) {
	name := mux.Vars(r)["social"]

	conf, ok := oauth2conf[name]
	if !ok {
		w.WriteHeader(http.StatusNotFound)
		return
	}

	ctx := context.Background()

	code := r.URL.Query().Get("code")
	if code == "" {
		log.Errorln("SOCIAL: Empty code.")
		w.WriteHeader(http.StatusForbidden)
		return
	}
	tok, err := conf.Exchange(ctx, code)
	if err != nil {
		log.Errorln("SOCIAL: Token retrieve error: ", err)
		w.WriteHeader(http.StatusForbidden)
		return
	}

	js, err := json.MarshalIndent(tok, "", "    ")
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	session, _ := store.Get(r, "bbg-auth")
	session.Values["social-json"] = js
	session.Save(r, w)

	w.Header().Set("Content-Type", "application/json")
	w.Write(js)
}
