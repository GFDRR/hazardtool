package thinkhazard

import scala.concurrent.duration._

import io.gatling.core.Predef._
import io.gatling.http.Predef._
import io.gatling.jdbc.Predef._

import org.asynchttpclient.util.Base64
import io.gatling.http.response._
import java.nio.charset.StandardCharsets.UTF_8

class ThinkhazardSimulation extends Simulation {

	val httpProtocol = http
		.baseURL("http://int.thinkhazard.org")
		.inferHtmlResources()
		.acceptHeader("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
		.acceptEncodingHeader("gzip, deflate")
		.acceptLanguageHeader("en-US,en;q=0.5")
		.userAgentHeader("Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:45.0) Gecko/20100101 Firefox/45.0")

	val ajax = Map(
		"X-Requested-With" -> "XMLHttpRequest")

  val json = Map(
    "Accept" -> "application/json, text/javascript, */*; q=0.01")

  object Index {
    val index = exec(http("index")
			.get("/")
      .resources(
            http("thinkhazard.ttf")
			.get("/static/399ba671a5a9807e657e6b9ae87a950a/webfonts/thinkhazard/fonts/thinkhazard.ttf?-xr90r9"),
            http("variable_black-webfont.woff2")
			.get("/static/399ba671a5a9807e657e6b9ae87a950a/webfonts/variable_black-webfont.woff2"),
            http("front-bg.png")
			.get("/static/611f7f617b5f933c63b5a07e6fa48705/images/front-bg.png")
			.header("Accept", "image/png,image/*;q=0.8,*/*;q=0.5")))
		  .pause(3)

		  .exec(http("administrativedivision?q=tur")
			  .get("/administrativedivision?q=tur")
			  .headers(ajax)
        .headers(json))
		  .pause(1)
		  .exec(http("administrativedivision?q=turke")
			  .get("/administrativedivision?q=turke")
			  .headers(ajax)
        .headers(json))
		  .pause(2)
  }

  object Report {
    var report = exec(http("COU")
			.get("/report/249-turkey")
			.resources(
            http("COU.json")
			.get("/report/249.json?resolution=4891.96981025128")))
		  .pause(4)

      // Country report by hazardtype
		  .exec(http("COU_FL")
			.get("/report/249-turkey/FL")
			.resources(
            http("COU_FL.json")
			.get("/report/249/FL.json?resolution=4891.96981025128")))
      .pause(2)

      .exec(http("COU_EQ")
			.get("/report/249-turkey/EQ")
      .resources(
            http("COU_EQ.json")
			.get("/report/249/EQ.json?resolution=4891.96981025128")))
      .pause(2)

      .exec(http("COU_DG")
			.get("/report/249-turkey/DG")
      .resources(
            http("COU_DG.json")
			.get("/report/249/DG.json?resolution=4891.96981025128")))
		  .pause(4)

      // Province
		  .exec(http("PRO_DG")
			.get("/report/3069-turkey-konya/DG")
			.resources(
            http("PRO_DG.json")
			.get("/report/3069/DG.json?resolution=1222.99245256282")))
      .pause(2)

      // Region
      .exec(http("REG_DG")
			.get("/report/28072-turkey-konya-meram/DG")
      .resources(
            http("REG_DG.json")
			.get("/report/28072/DG.json?resolution=305.748113140705")))
		  .pause(2)

      // data_source
		  .exec(http("data_source")
			.get("/data_source/DR-GLOBAL-IVM-WCI")
			.headers(ajax))
  }

  object Pdf {
    var pdf = exec(http("report/create")
			.post("/report/create/249")
			.headers(ajax)
      .check(jsonPath("$.report_id").saveAs("report_id")))
    .exec(session =>
      session.set("status", "running"))
    .pause(1)
    .asLongAs(session => session("status").as[String].equals("running")) {
        exec(http("report/status")
          .get("/report/status/249/${report_id}.json")
          .headers(ajax)
          .check(jsonPath("$.status").saveAs("status")))
          .pause(1)
    }
    .doIf(session => session("status").as[String].equals("done")) {
        exec(http("report_pdf")
			    .get("/report/249/${report_id}.pdf")
          .transformResponse { case response if response.isReceived =>
            new ResponseWrapper(response) {
              override val body = new ByteArrayResponseBody(response.body.bytes, UTF_8)
            }
          })
    }
  }

	val users = scenario("RecordedSimulation").exec(Index.index, Report.report)
  val users_pdf = scenario("RecordedSimulation").exec(Index.index, Report.report , Pdf.pdf) 

	setUp(
    users.inject(rampUsers(30) over (10 seconds))
    //users_pdf.inject(rampUsers(30) over (10 seconds))
  ).protocols(httpProtocol)
}
