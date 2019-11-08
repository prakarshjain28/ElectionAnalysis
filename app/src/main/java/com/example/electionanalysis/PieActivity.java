package com.example.electionanalysis;

import androidx.appcompat.app.AppCompatActivity;

import android.graphics.Color;
import android.graphics.Paint;
import android.os.Bundle;

import com.github.mikephil.charting.charts.PieChart;
import com.github.mikephil.charting.components.AxisBase;
import com.github.mikephil.charting.components.XAxis;
import com.github.mikephil.charting.data.Entry;
import com.github.mikephil.charting.data.PieData;
import com.github.mikephil.charting.data.PieDataSet;
import com.github.mikephil.charting.data.PieEntry;
import com.github.mikephil.charting.formatter.IAxisValueFormatter;
import com.github.mikephil.charting.utils.ColorTemplate;
import com.google.android.gms.tasks.Task;
import com.google.firebase.firestore.DocumentReference;
import com.google.firebase.firestore.DocumentSnapshot;
import com.google.firebase.firestore.FirebaseFirestore;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;

public class PieActivity extends AppCompatActivity {
    FirebaseFirestore db;
    double bjp_p,bjp_n,congress_p,congress_n,mns_p,mns_n,ncp_p,ncp_n,shivsena_p,shivsena_n,others;
    Map<String,Object > number =new HashMap<>();
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_pie);
        db=FirebaseFirestore.getInstance();
        final DocumentReference docRef=db.collection("data").document("sentiment");
        Task<DocumentSnapshot> task = docRef.get();
        while(task.isComplete() == false){
            System.out.println("busy wait goals");
        }
        DocumentSnapshot document= task.getResult();
        number = document.getData();
        bjp_p=(long)number.get("bjp_positive");
        bjp_n=(long)number.get("bjp_negative");
        congress_p=(long)number.get("congress_positive");
        congress_n=(long)number.get("congress_negative");
        mns_p=(long)number.get("mns_positive");
        mns_n=(long)number.get("mns_negative");
        ncp_p=(long)number.get("ncp_positive");
        ncp_n=(long)number.get("ncp_negative");
        shivsena_p=(long)number.get("shivsena_positive");
        shivsena_n=(long)number.get("shivsena_negative");
        PieChart pieChart =(PieChart) findViewById(R.id.piechart);
        PieChart pieChart1 =(PieChart) findViewById(R.id.piechart1);
        PieChart pieChart2 =(PieChart) findViewById(R.id.piechart2);
        PieChart pieChart3 =(PieChart) findViewById(R.id.piechart3);
        PieChart pieChart4 =(PieChart) findViewById(R.id.piechart4);

        ArrayList bjp_senti = new ArrayList();
        double temp=bjp_p;
        bjp_p=(bjp_p/(temp+bjp_n))*100;
        bjp_n=(bjp_n/(temp+bjp_n))*100;
        System.out.println("BJP POSITVE "+bjp_p);
        bjp_senti.add(new PieEntry( (int)bjp_p,"Positive"));
        bjp_senti.add(new PieEntry( (int)bjp_n,"Negative"));

        PieDataSet pieDataSet = new PieDataSet(bjp_senti,"");

        pieDataSet.setColors(Color.rgb(62,174,145), Color.rgb(228,64,51));
        PieData pieData = new PieData(pieDataSet);
        pieChart.setData(pieData);
        pieChart.getDescription().setTextSize(16f);
        pieChart.animateXY(3000, 3000);
        pieDataSet.setValueTextSize(20);
        pieChart.getDescription().setTextAlign(Paint.Align.LEFT);
        pieChart.invalidate();

        ArrayList cong_senti = new ArrayList();
        double temp1=congress_p;
        congress_p=(congress_p/(temp1+congress_n))*100;
        congress_n=(congress_n/(temp1+congress_n))*100;
        System.out.println("Congress POSITVE "+congress_p);
        cong_senti.add(new PieEntry( (int)congress_p,"Positive"));
        cong_senti.add(new PieEntry( (int)congress_n,"Negative"));

        PieDataSet pieDataSet1 = new PieDataSet(cong_senti,"");
        pieDataSet1.setColors(Color.rgb(62,174,145), Color.rgb(228,64,51));
        PieData pieData1 = new PieData(pieDataSet1);
        pieChart1.setData(pieData1);
        pieChart1.animateXY(3000, 3000);
        pieDataSet1.setValueTextSize(20);
        pieChart1.getDescription().setTextAlign(Paint.Align.LEFT);
        pieChart1.invalidate();

        ArrayList mns_senti = new ArrayList();
        double temp2=mns_p;
        mns_p=(mns_p/(temp2+mns_n))*100;
        mns_n=(mns_n/(temp2+mns_n))*100;
        System.out.println("MNS POSITVE "+mns_p);
        mns_senti.add(new PieEntry( (int)mns_p,"Positive"));
        mns_senti.add(new PieEntry( (int)mns_n,"Negative"));

        PieDataSet pieDataSet2 = new PieDataSet(mns_senti,"");
        pieDataSet2.setColors(Color.rgb(62,174,145), Color.rgb(228,64,51));
        PieData pieData2 = new PieData(pieDataSet2);
        pieChart2.setData(pieData2);
        pieChart2.animateXY(3000, 3000);
        pieDataSet2.setValueTextSize(20);
        pieChart2.getDescription().setTextAlign(Paint.Align.LEFT);
        pieChart2.invalidate();

        ArrayList ncp_senti = new ArrayList();
        double temp3=ncp_p;
        ncp_p=(ncp_p/(temp3+ncp_n))*100;
        ncp_n=(ncp_n/(temp3+ncp_n))*100;
        System.out.println("ncp POSITVE "+ncp_p);
        ncp_senti.add(new PieEntry( (int)ncp_p,"Positive"));
        ncp_senti.add(new PieEntry( (int)ncp_n,"Negative"));

        PieDataSet pieDataSet3 = new PieDataSet(ncp_senti,"");
        pieDataSet3.setColors(Color.rgb(62,174,145), Color.rgb(228,64,51));
        PieData pieData3= new PieData(pieDataSet3);
        pieChart3.setData(pieData3);
        pieChart3.animateXY(3000, 3000);
        pieDataSet3.setValueTextSize(20);
        pieChart3.getDescription().setTextAlign(Paint.Align.LEFT);
        pieChart3.invalidate();

        ArrayList shiv_senti = new ArrayList();
        double temp4=shivsena_p;
        shivsena_p=(shivsena_p/(temp4+shivsena_n))*100;
        shivsena_n=(shivsena_n/(temp4+shivsena_n))*100;
        System.out.println("ShivSena POSITVE "+shivsena_p);
        shiv_senti.add(new PieEntry( (int)shivsena_p,"Positive"));
        shiv_senti.add(new PieEntry( (int)shivsena_n,"Negative"));

        PieDataSet pieDataSet4 = new PieDataSet(shiv_senti,"");
        pieDataSet4.setColors(Color.rgb(62,174,145), Color.rgb(228,64,51));
        PieData pieData4 = new PieData(pieDataSet4);
        pieChart4.setData(pieData4);
        pieChart4.animateXY(3000, 3000);
        pieDataSet4.setValueTextSize(20);
        pieChart4.getDescription().setTextAlign(Paint.Align.LEFT);
        pieChart4.invalidate();
    }
}
